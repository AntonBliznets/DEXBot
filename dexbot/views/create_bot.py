from PyQt5 import QtWidgets

from dexbot.views.notice import NoticeDialog
from dexbot.views.gen.create_bot_window import Ui_Dialog


class CreateBotView(QtWidgets.QDialog):

    def __init__(self, controller):
        super().__init__()
        self.controller = controller

        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        # Todo: Using a model here would be more Qt like
        self.ui.strategy_input.addItems(self.controller.strategies)

        self.bot_name = controller.get_unique_bot_name()
        self.ui.bot_name_input.setText(self.bot_name)

        self.ui.save_button.clicked.connect(self.handle_save)
        self.ui.cancel_button.clicked.connect(self.handle_cancel)

    def validate_bot_name(self):
        bot_name = self.ui.bot_name_input.text()
        return self.controller.is_bot_name_valid(bot_name)

    def validate_asset(self, asset):
        return self.controller.is_asset_valid(asset)

    def validate_market(self):
        base_asset = self.ui.base_asset_input.text()
        quote_asset = self.ui.quote_asset_input.text()
        return base_asset.lower() != quote_asset.lower()

    def validate_account_name(self):
        account = self.ui.account_input.text()
        return self.controller.account_exists(account)

    def validate_account(self):
        account = self.ui.account_input.text()
        private_key = self.ui.private_key_input.text()
        return self.controller.is_account_valid(account, private_key)

    def validate_form(self):
        error_text = ''
        base_asset = self.ui.base_asset_input.text()
        quote_asset = self.ui.quote_asset_input.text()
        if not self.validate_bot_name():
            bot_name = self.ui.bot_name_input.text()
            error_text = 'Bot name needs to be unique. "{}" is already in use.'.format(bot_name)
        elif not self.validate_asset(base_asset):
            error_text = 'Field "Base Asset" does not have a valid asset.'
        elif not self.validate_asset(quote_asset):
            error_text = 'Field "Base Quote" does not have a valid asset.'
        elif not self.validate_market():
            error_text = "Market {}/{} doesn't exist.".format(base_asset, quote_asset)
        elif not self.validate_account_name():
            error_text = "Account doesn't exist."
        elif not self.validate_account():
            error_text = 'Private key is invalid.'

        if error_text:
            dialog = NoticeDialog(error_text)
            dialog.exec_()
            return False
        else:
            return True

    def handle_save(self):
        if not self.validate_form():
            return

        self.bot_name = self.ui.bot_name_input.text()
        account = self.ui.account_input.text()
        market = '{}:{}'.format(self.ui.base_asset_input, self.ui.quote_asset_input)
        strategy = self.ui.strategy_input.currentText()
        bot_module = self.controller.get_strategy_module(strategy)
        bot_data = {
            'account': account,
            'market': market,
            'module': bot_module,
            'strategy': strategy
        }
        self.controller.add_bot_config(self.bot_name, bot_data)
        self.accept()

    def handle_cancel(self):
        self.reject()
