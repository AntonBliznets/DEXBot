import importlib
import time, sys
import logging
import os.path
from multiprocessing import Process

from bitshares.notify import Notify
from bitshares.instance import shared_bitshares_instance

log = logging.getLogger(__name__)


# FIXME: currently static list of bot strategies: ? how to enumerate bots available and deploy new bot strategies.

STRATEGIES=[('dexbot.strategies.echo',"Echo Test"),
            ('dexbot.strategies.follow_orders',"Haywood's Follow Orders")]

log_bots = logging.getLogger('dexbot.per_bot')
# NOTE this is the  special logger for per-bot events
# it  returns LogRecords with extra fields: botname, account, market and is_disabled
# is_disabled is a callable returning True if the bot is currently disabled.
# GUIs can add a handler to this logger to get a stream of events re the running bots.


class BotInfrastructure(Process):

    bots = dict()

    def __init__(
        self,
        config,
        bitshares_instance=None,
        gui_data=None
    ):
        super().__init__()
        # BitShares instance
        self.bitshares = bitshares_instance or shared_bitshares_instance()

        self.config = config

        # set the module search path
        user_bot_path = os.path.expanduser("~/bots")
        if os.path.exists(user_bot_path):
            sys.path.append(user_bot_path)

        # Load all accounts and markets in use to subscribe to them
        accounts = set()
        markets = set()
        
        # Initialize bots:
        for botname, bot in config["bots"].items():
            if "account" not in bot:
                log_bots.critical("Bot has no account",extra={'botname':botname,'account':'unknown','market':'unknown','is_dsabled':(lambda: True)})
                continue
            if "market" not in bot:
                log_bots.critical("Bot has no market",extra={'botname':botname,'account':bot['account'],'market':'unknown','is_disabled':(lambda: True)})
                continue
            try:
                klass = getattr(
                    importlib.import_module(bot["module"]),
                    'Strategy'
                )
                self.bots[botname] = klass(
                    config=config,
                    name=botname,
                    bitshares_instance=self.bitshares,
                    gui_data=gui_data
                )
                markets.add(bot['market'])
                accounts.add(bot['account'])
            except:
                log_bots.exception("Bot initialisation",extra={'botname':botname,'account':bot['account'],'market':'unknown','is_disabled':(lambda: True)})

        if len(markets) == 0:
            log.critical("No bots to launch, exiting")
            sys.exit(70) # 70= "Software error" in /usr/include/sysexts.h
        # Create notification instance
        # Technically, this will multiplex markets and accounts and
        # we need to demultiplex the events after we have received them
        self.notify = Notify(
            markets=list(markets),
            accounts=list(accounts),
            on_market=self.on_market,
            on_account=self.on_account,
            on_block=self.on_block,
            bitshares_instance=self.bitshares
        )

    # Events
    def on_block(self, data):
        for botname, bot in self.config["bots"].items():
            if (not botname in self.bots) or self.bots[botname].disabled:
                continue
            try:
                self.bots[botname].ontick(data)
            except Exception as e:
                self.bots[botname].error_ontick(e)
                self.bots[botname].log.exception("in .tick()")

    def on_market(self, data):
        if data.get("deleted", False):  # no info available on deleted orders
            return
        for botname, bot in self.config["bots"].items():
            if self.bots[botname].disabled:
                continue
            if bot["market"] == data.market:
                try:
                    self.bots[botname].onMarketUpdate(data)
                except Exception as e:
                    self.bots[botname].error_onMarketUpdate(e)
                    self.bots[botname].log.exception(".onMarketUpdate()")

    def on_account(self, accountupdate):
        account = accountupdate.account
        for botname, bot in self.config["bots"].items():
            if self.bots[botname].disabled:
                self.bots[botname].log.info("bot disabled" % botname)
                continue
            if bot["account"] == account["name"]:
                try:
                    self.bots[botname].onAccount(accountupdate)
                except Exception as e:
                    self.bots[botname].error_onAccount(e)
                    self.bots[botname].log.exception(".onAccountUpdate()")

    def run(self):
        self.notify.listen()
