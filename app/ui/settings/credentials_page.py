from PySide6 import QtWidgets, QtCore
from ..dayu_widgets.label import MLabel
from ..dayu_widgets.line_edit import MLineEdit
from ..dayu_widgets.check_box import MCheckBox
from ..dayu_widgets.push_button import MPushButton
from .utils import set_label_width

class CredentialsPage(QtWidgets.QWidget):
    def __init__(self, services: list[str], value_mappings: dict[str, str], parent=None):
        super().__init__(parent)
        self.services = services
        self.value_mappings = value_mappings
        self.credential_widgets: dict[str, MLineEdit] = {}

        # main layout (no internal scroll here — outer settings scroll handles it)
        main_layout = QtWidgets.QVBoxLayout(self)
        content_layout = QtWidgets.QVBoxLayout()

        self.save_keys_checkbox = MCheckBox(self.tr("Save Keys"))

        info_label = MLabel(self.tr(
            "These settings are for advanced users who wish to use their own Custom API endpoints (e.g. Local Language Models) for translation. "
            "For most users, no configuration is needed here."
        )).secondary()
        info_label.setWordWrap(True)
        
        content_layout.addWidget(info_label)
        content_layout.addSpacing(10)
        content_layout.addWidget(self.save_keys_checkbox)
        content_layout.addSpacing(20)

        for service_label in self.services:
            service_layout = QtWidgets.QVBoxLayout()
            service_header = MLabel(service_label).strong()
            service_header.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
            service_layout.addWidget(service_header)

            normalized = self.value_mappings.get(service_label, service_label)

            if normalized == "Microsoft Azure":
                # OCR
                ocr_label = MLabel(self.tr("OCR")).secondary()
                service_layout.addWidget(ocr_label)

                ocr_api_key_input = MLineEdit()
                ocr_api_key_input.setEchoMode(QtWidgets.QLineEdit.Password)
                ocr_api_key_input.setFixedWidth(400)
                ocr_api_key_prefix = MLabel(self.tr("API Key")).border()
                set_label_width(ocr_api_key_prefix)
                ocr_api_key_prefix.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                ocr_api_key_input.set_prefix_widget(ocr_api_key_prefix)
                service_layout.addWidget(ocr_api_key_input)
                self.credential_widgets["Microsoft Azure_api_key_ocr"] = ocr_api_key_input

                endpoint_input = MLineEdit()
                endpoint_input.setFixedWidth(400)
                endpoint_prefix = MLabel(self.tr("Endpoint URL")).border()
                set_label_width(endpoint_prefix)
                endpoint_prefix.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                endpoint_input.set_prefix_widget(endpoint_prefix)
                service_layout.addWidget(endpoint_input)
                self.credential_widgets["Microsoft Azure_endpoint"] = endpoint_input

                # Translator
                # # Translator
                # translate_label = MLabel(self.tr("Translate")).secondary()
                # service_layout.addWidget(translate_label)

                # translator_api_key_input = MLineEdit()
                # translator_api_key_input.setEchoMode(QtWidgets.QLineEdit.Password)
                # translator_api_key_input.setFixedWidth(400)
                # translator_api_key_prefix = MLabel(self.tr("API Key")).border()
                # set_label_width(translator_api_key_prefix)
                # translator_api_key_prefix.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                # translator_api_key_input.set_prefix_widget(translator_api_key_prefix)
                # service_layout.addWidget(translator_api_key_input)
                # self.credential_widgets["Microsoft Azure_api_key_translator"] = translator_api_key_input

                # region_input = MLineEdit()
                # region_input.setFixedWidth(400)
                # region_prefix = MLabel(self.tr("Region")).border()
                # set_label_width(region_prefix)
                # region_prefix.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                # region_input.set_prefix_widget(region_prefix)
                # service_layout.addWidget(region_input)
                # self.credential_widgets["Microsoft Azure_region"] = region_input

            elif normalized == "Custom":
                api_key_input = MLineEdit()
                api_key_input.setEchoMode(QtWidgets.QLineEdit.Password)
                api_key_input.setFixedWidth(400)
                api_key_prefix = MLabel(self.tr("API Key")).border()
                set_label_width(api_key_prefix)
                api_key_prefix.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                api_key_input.set_prefix_widget(api_key_prefix)
                service_layout.addWidget(api_key_input)
                self.credential_widgets[f"{normalized}_api_key"] = api_key_input

                endpoint_input = MLineEdit()
                endpoint_input.setFixedWidth(400)
                endpoint_prefix = MLabel(self.tr("Endpoint URL")).border()
                set_label_width(endpoint_prefix)
                endpoint_prefix.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                endpoint_input.set_prefix_widget(endpoint_prefix)
                service_layout.addWidget(endpoint_input)
                self.credential_widgets[f"{normalized}_api_url"] = endpoint_input

                model_input = MLineEdit()
                model_input.setFixedWidth(400)
                model_prefix = MLabel(self.tr("Model")).border()
                set_label_width(model_prefix)
                model_prefix.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                model_input.set_prefix_widget(model_prefix)
                service_layout.addWidget(model_input)
                self.credential_widgets[f"{normalized}_model"] = model_input

                temperature_input = MLineEdit()
                temperature_input.setFixedWidth(400)
                temperature_input.setPlaceholderText("0.2")
                temperature_prefix = MLabel(self.tr("Temperature")).border()
                set_label_width(temperature_prefix)
                temperature_prefix.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                temperature_input.set_prefix_widget(temperature_prefix)
                service_layout.addWidget(temperature_input)
                self.credential_widgets[f"{normalized}_temperature"] = temperature_input

                service_hint = MLabel(self.tr(
                    "Leave the API Key empty for a local server. If the Endpoint URL is "
                    "empty, a local server (Ollama, LM Studio) is detected automatically "
                    "and its first model is used."
                )).secondary()
                service_hint.setWordWrap(True)
                service_layout.addWidget(service_hint)

            elif normalized == "Yandex":
                api_key_input = MLineEdit()
                api_key_input.setEchoMode(QtWidgets.QLineEdit.Password)
                api_key_input.setFixedWidth(400)
                api_key_prefix = MLabel(self.tr("Secret Key")).border()
                set_label_width(api_key_prefix)
                api_key_prefix.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                api_key_input.set_prefix_widget(api_key_prefix)
                service_layout.addWidget(api_key_input)
                self.credential_widgets[f"{normalized}_api_key"] = api_key_input

                folder_id_input = MLineEdit()
                folder_id_input.setFixedWidth(400)
                folder_id_prefix = MLabel(self.tr("Folder ID")).border()
                set_label_width(folder_id_prefix)
                folder_id_prefix.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                folder_id_input.set_prefix_widget(folder_id_prefix)
                service_layout.addWidget(folder_id_input)
                self.credential_widgets[f"{normalized}_folder_id"] = folder_id_input

            else:
                api_key_input = MLineEdit()
                api_key_input.setEchoMode(QtWidgets.QLineEdit.Password)
                api_key_input.setFixedWidth(400)
                api_key_prefix = MLabel(self.tr("API Key")).border()
                set_label_width(api_key_prefix)
                api_key_prefix.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                api_key_input.set_prefix_widget(api_key_prefix)
                service_layout.addWidget(api_key_input)
                self.credential_widgets[f"{normalized}_api_key"] = api_key_input

            content_layout.addLayout(service_layout)
            content_layout.addSpacing(20)

        content_layout.addLayout(self._build_network_section())
        content_layout.addSpacing(20)

        content_layout.addStretch(1)
        main_layout.addLayout(content_layout)

    def _build_network_section(self) -> QtWidgets.QVBoxLayout:
        """Proxy settings for the Custom translator's outbound calls."""
        section = QtWidgets.QVBoxLayout()
        section.addWidget(MLabel(self.tr("Network")).strong())

        hint = MLabel(self.tr(
            "Route Custom and OpenAI-compatible API requests through an HTTP proxy. "
            "Leave empty to use the HTTPS_PROXY / HTTP_PROXY environment variables. "
            "Local model servers are always connected to directly, so this only "
            "affects hosted APIs."
        )).secondary()
        hint.setWordWrap(True)
        section.addWidget(hint)

        self.proxy_input = MLineEdit()
        self.proxy_input.setFixedWidth(400)
        self.proxy_input.setPlaceholderText("http://127.0.0.1:8080")
        proxy_prefix = MLabel(self.tr("Proxy")).border()
        set_label_width(proxy_prefix)
        proxy_prefix.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.proxy_input.set_prefix_widget(proxy_prefix)
        section.addWidget(self.proxy_input)
        self.network_widgets = {"proxy_url": self.proxy_input}

        self.test_connection_button = MPushButton(self.tr("Test Connection"))
        self.test_connection_label = MLabel("").secondary()
        self.test_connection_label.setWordWrap(True)
        section.addWidget(self.test_connection_button)
        section.addWidget(self.test_connection_label)

        return section
