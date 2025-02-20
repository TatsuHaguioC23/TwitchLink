from Core.App import App
from Core.Updater import Updater
from Core.Ui import *
from Services.Messages import Messages
from Services.Image.Loader import ImageLoader
from Services.Document import DocumentData, DocumentButtonData
from Services.Logging.ErrorDetector import ErrorDetector, ErrorHandlers
from Services.NotificationManager import NotificationManager
from Download.DownloadManager import DownloadManager
from Ui.Components.Operators.NavigationBar import NavigationBar
from Ui.Components.Pages.SearchPage import SearchPage
from Ui.Components.Pages.DownloadsPage import DownloadsPage
from Ui.Components.Pages.AccountPage import AccountPage
from Ui.Components.Pages.InformationPage import InformationPage
from Ui.Components.Widgets.ProgressDialog import ProgressDialog


class MainWindow(QtWidgets.QMainWindow, UiFile.mainWindow, WindowGeometryManager):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent=parent)
        App.appStarted.connect(self.start, QtCore.Qt.QueuedConnection)

    def start(self):
        if DB.setup.needSetup():
            if Ui.Setup().exec():
                App.restart()
            else:
                App.exit()
        else:
            Ui.Loading().exec()
            self.loadWindowGeometry()
            self.loadComponents()
            self.setup()

    def loadComponents(self):
        self.setWindowIcon(QtGui.QIcon(Icons.APP_LOGO_ICON))
        self.actionGettingStarted.triggered.connect(self.gettingStarted)
        self.actionAbout.triggered.connect(self.openAbout)
        self.actionTermsOfService.triggered.connect(self.openTermsOfService)
        self.actionSponsor.triggered.connect(self.sponsor)
        self.navigationBar = NavigationBar(self.navigationArea, parent=self)
        self.navigationBar.focusChanged.connect(self.onFocusChange)
        self.searchPageObject = self.navigationBar.addPage(self.searchPageButton, self.searchPage, icon=Icons.SEARCH_ICON)
        self.downloadsPageObject = self.navigationBar.addPage(self.downloadsPageButton, self.downloadsPage, icon=Icons.DOWNLOAD_ICON)
        self.accountPageObject = self.navigationBar.addPage(self.accountPageButton, self.accountPage, icon=Icons.ACCOUNT_ICON)
        self.settingsPageObject = self.navigationBar.addPage(self.settingsPageButton, self.settingsPage, icon=Icons.SETTINGS_ICON)
        self.informationPageObject = self.navigationBar.addPage(self.informationPageButton, self.informationPage, icon=Icons.INFO_ICON)
        self.search = SearchPage(self.searchPageObject, parent=self)
        self.search.accountPageShowRequested.connect(self.accountPageObject.show)
        self.searchPage.layout().addWidget(self.search)
        self.downloads = DownloadsPage(self.downloadsPageObject, parent=self)
        self.downloads.accountPageShowRequested.connect(self.accountPageObject.show)
        self.downloads.appShutdownRequested.connect(self.shutdown)
        self.downloads.systemShutdownRequested.connect(self.shutdownSystem)
        self.downloadsPage.layout().addWidget(self.downloads)
        self.account = AccountPage(self.accountPageObject, parent=self)
        self.accountPage.layout().addWidget(self.account)
        self.settings = Ui.Settings(parent=self)
        self.settings.restartRequired.connect(self.restart)
        self.settingsPage.layout().addWidget(self.settings)
        self.information = InformationPage(self.informationPageObject, parent=self)
        self.information.accountRefreshRequested.connect(self.account.refreshAccount)
        self.information.appShutdownRequested.connect(self.shutdown)
        self.informationPage.layout().addWidget(self.information)

    def setup(self):
        self.statusUpdated(isInSetup=True)
        if Updater.status.isOperational():
            if DB.setup.getTermsOfServiceAgreement() == None:
                self.openTermsOfService()
            else:
                self.account.refreshAccount()
            Updater.statusUpdated.connect(self.statusUpdated)
            Updater.startAutoUpdate()
        self.show()
        self.showErrorHistory()

    def statusUpdated(self, isInSetup=False):
        isOperational = Updater.status.isOperational()
        hasDownloaders = self.downloads.downloads.getPreviewCount() != 0
        self.menuBar().setEnabled(isOperational or hasDownloaders)
        if not isOperational and hasDownloaders:
            self.downloadsPageObject.focus()
            self.settingsPageObject.focus()
        else:
            self.downloadsPageObject.unfocus()
            self.settingsPageObject.unfocus()
        DownloadManager.setDownloaderCreationEnabled(isOperational)
        contentId = f"APP_STATUS"
        self.information.removeAppInfo(contentId)
        status = Updater.status.getStatus()
        if status == Updater.status.CONNECTION_FAILURE:
            if isInSetup:
                content = T("#Please try again later.")
                buttons = [
                    DocumentButtonData(text="ok", action=self.shutdown, role="action", default=True)
                ]
            else:
                content = T("#Some features will be temporarily disabled.\nPlease wait.\nWhen the connection is restored, those features will be activated.")
                buttons = []
            self.information.showAppInfo(
                DocumentData(
                    contentId=contentId,
                    title=T("network-error"),
                    content=f"{T('#A network error occurred while connecting to the server.')}\n{content}",
                    contentType="text",
                    modal=True,
                    buttons=buttons
                )
            )
        elif status == Updater.status.UNEXPECTED_ERROR:
            Updater.stopAutoUpdate()
            if isInSetup:
                content = T("#Please try again later.")
                buttons = [
                    DocumentButtonData(text="ok", action=self.shutdown, role="action", default=True)
                ]
            else:
                content = f"{T('#Some features will be disabled.')}\n{T('#Please restart the app.')}"
                buttons = []
            self.information.showAppInfo(
                DocumentData(
                    contentId=contentId,
                    title=T("error"),
                    content=f"{T('#An unexpected error occurred while connecting to the server.')}\n{content}",
                    contentType="text",
                    modal=True,
                    buttons=buttons
                )
            )
        elif status == Updater.status.SESSION_EXPIRED:
            Updater.stopAutoUpdate()
            self.information.showAppInfo(
                DocumentData(
                    contentId=contentId,
                    title=T("session-expired"),
                    content=f"{T('#Your session has expired.')}\n{T('#Some features will be disabled.')}\n{T('#Please restart the app.')}",
                    contentType="text",
                    modal=True,
                    buttons=[]
                )
            )
        elif status == Updater.status.UNAVAILABLE:
            self.information.showAppInfo(
                DocumentData(
                    contentId=contentId,
                    title=T("service-unavailable"),
                    content=Updater.status.operationalInfo or T("#{appName} is currently unavailable.", appName=Config.APP_NAME),
                    contentType=Updater.status.operationalInfoType or "text",
                    modal=True,
                    buttons=[DocumentButtonData(text="ok", action=self.shutdown, role="action", default=True)] if isInSetup else []
                )
            )
            if not isInSetup:
                self.restart()
        elif status == Updater.status.UPDATE_REQUIRED or status == Updater.status.UPDATE_FOUND:
            if status == Updater.status.UPDATE_REQUIRED:
                Updater.stopAutoUpdate()
            self.information.showAppInfo(
                DocumentData(
                    contentId=contentId,
                    title=T("recommended-update" if status == Updater.status.UPDATE_FOUND else "required-update"),
                    content=Updater.status.version.updateNote or f"{T('#A new version of {appName} has been released!', appName=Config.APP_NAME)}\n\n[{Config.APP_NAME} {Updater.status.version.latestVersion}]",
                    contentType=Updater.status.version.updateNoteType if Updater.status.version.updateNote else "text",
                    modal=status == Updater.status.UPDATE_REQUIRED,
                    buttons=[
                        DocumentButtonData(text=T("update"), action=self.confirmUpdateShutdown, role="action", default=True),
                        DocumentButtonData(text=T("cancel"), action=(self.shutdown if isInSetup else self.confirmShutdown) if status == Updater.status.UPDATE_REQUIRED else None, role="reject", default=False)
                    ]
                ),
                icon=Icons.UPDATE_FOUND_ICON
            )

    def showErrorHistory(self):
        for key in ErrorHandlers.getHandlerDict():
            if ErrorDetector.hasHistory(key):
                if ErrorDetector.getHistory(key) > ErrorDetector.MAX_IGNORE_COUNT:
                    errorInfo = T("#We detected an error and disabled some features.\nClick '{buttonText}' to try again.", buttonText=T("delete-error-history"))
                    errorMessages = "\n".join(map(T, ErrorHandlers.getHandler(key).errorMessages))
                    contactInfo = T("#If the error persists, contact the developer.")
                    if self.ask("error", f"{errorInfo}\n\n{key}: {ErrorDetector.getHistory(key)}\n\n{errorMessages}\n\n{contactInfo}", contentTranslate=False, okText="delete-error-history", cancelText="ok"):
                        ErrorDetector.deleteHistory(key)
                        self.info("warning", "#Some features may not be activated until the app is restarted.")

    def onFocusChange(self, focus):
        enabled = not focus
        self.actionAbout.setEnabled(enabled)
        self.actionTermsOfService.setEnabled(enabled)

    def confirmShutdown(self):
        if DownloadManager.isDownloaderRunning() and not DownloadManager.isShuttingDown():
            if self.ask(*Messages.ASK.STOP_CANCEL_ALL_DOWNLOADS):
                self.shutdown()
        elif DB.general.isConfirmExitEnabled():
            if self.ask("notification", "#Are you sure you want to exit?"):
                self.shutdown()
        else:
            self.shutdown()

    def confirmUpdateShutdown(self):
        if DownloadManager.isDownloaderRunning() and not DownloadManager.isShuttingDown():
            if not Utils.ask(*Messages.ASK.STOP_CANCEL_ALL_DOWNLOADS):
                return
        Utils.openUrl(Utils.joinUrl(Updater.status.version.updateUrl, params={"lang": DB.localization.getLanguage()}))
        self.shutdown()

    def closeEvent(self, event):
        super().closeEvent(event)
        event.ignore()
        self.confirmShutdown()

    def gettingStarted(self):
        Utils.openUrl(Utils.joinUrl(Config.HOMEPAGE_URL, "help", params={"lang": DB.localization.getLanguage()}))

    def openAbout(self):
        self.information.openAbout()

    def openTermsOfService(self):
        self.information.openTermsOfService()

    def sponsor(self):
        Utils.openUrl(Utils.joinUrl(Config.HOMEPAGE_URL, "donate", params={"lang": DB.localization.getLanguage()}))

    def cleanup(self):
        DownloadManager.cancelAll()
        ImageLoader.threadPool.clear()
        DownloadManager.waitAll()
        ImageLoader.threadPool.waitForDone()

    def waitForCleanup(self):
        if DownloadManager.isDownloaderRunning() or ImageLoader.threadPool.activeThreadCount() != 0:
            msg = ProgressDialog(cancelAllowed=False, parent=self)
            msg.setWindowTitle(T("shutting-down"))
            msg.setLabelText(T("#Shutting down all downloads" if DownloadManager.isDownloaderRunning() else "shutting-down", ellipsis=True))
            msg.setRange(0, 0)
            msg.exec(target=self.cleanup)

    def restart(self):
        self.shutdown(restart=True)

    def shutdown(self, restart=False):
        Updater.stopAutoUpdate()
        NotificationManager.clearAll()
        self.downloads.setDownloadCompleteAction(None)
        self.waitForCleanup()
        self.saveWindowGeometry()
        if restart:
            App.restart()
        else:
            App.exit()

    def shutdownSystem(self):
        self.shutdown()
        Utils.shutdownSystem(message=T("#Shutdown by {appName}'s scheduled task.", appName=Config.APP_NAME))