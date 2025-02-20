from Core.Ui import *
from Services import ContentManager
from Download.DownloadManager import DownloadManager


class PreviewWidgetItem(QtWidgets.QListWidgetItem):
    def __init__(self, downloaderId, parent=None):
        super(PreviewWidgetItem, self).__init__(parent=parent)
        self.widget = Ui.DownloadPreview(downloaderId, parent=parent)
        self.widget.setContentsMargins(10, 10, 10, 10)
        self.widget.resizedSignal.connect(self.resize)
        self.resize()

    def resize(self):
        self.setSizeHint(self.widget.sizeHint())


class Downloads(QtWidgets.QWidget, UiFile.downloads):
    progressWindowRequested = QtCore.pyqtSignal(object)
    downloadHistoryRequested = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(Downloads, self).__init__(parent=parent)
        self.previewItems = {}
        self.typeFilter.currentIndexChanged.connect(self.updateFilter)
        self.statusFilter.currentIndexChanged.connect(self.updateFilter)
        self.updateFilter()
        self.infoIcon = Utils.setSvgIcon(self.infoIcon, Icons.STORAGE_ICON)
        self.stackedWidget.setStyleSheet(f"#stackedWidget {{background-color: {self.stackedWidget.palette().color(QtGui.QPalette.Base).name()};}}")
        self.previewWidgetView.itemSelectionChanged.connect(self.previewWidgetView.clearSelection)
        self.previewWidgetView.itemClicked.connect(self.openProgressWindow)
        self.previewWidgetView.verticalScrollBar().setSingleStep(30)
        self.showPreviewCount()
        self.downloadHistoryButton.clicked.connect(self.downloadHistoryRequested)
        self.downloadCompleteActionInfo.clicked.connect(self.showDownloadCompleteActionInfo)
        ContentManager.ContentManager.restrictionsUpdated.connect(self.restrictionsUpdated)

    def downloaderCreated(self, downloaderId):
        item = PreviewWidgetItem(downloaderId=downloaderId)
        self.previewItems[downloaderId] = item
        self.previewWidgetView.setMinimumWidth(item.sizeHint().width() + self.previewWidgetView.verticalScrollBar().sizeHint().width())
        self.previewWidgetView.insertItem(0, item)
        self.previewWidgetView.setItemWidget(item, item.widget)
        self.processPreview(downloaderId)

    def downloaderDestroyed(self, downloaderId):
        self.previewWidgetView.takeItem(self.previewWidgetView.row(self.previewItems.pop(downloaderId)))
        self.showPreviewCount()

    def downloadStarted(self, downloaderId):
        self.processPreview(downloaderId)

    def downloadCompleted(self, downloaderId):
        self.processPreview(downloaderId)

    def processCompleteEvent(self, downloaderId):
        self.previewItems[downloaderId].widget.processCompleteEvent()

    def processPreview(self, downloaderId):
        self.setPreviewHidden(downloaderId, not self.filterPreview(downloaderId))
        self.showPreviewCount()

    def setPreviewHidden(self, downloaderId, hidden):
        self.previewItems[downloaderId].setHidden(hidden)

    def getPreviewCount(self):
        return len(self.previewItems)

    def showPreviewCount(self):
        self.totalCount.setText(self.getPreviewCount())
        previewCount = self.getFilteredPreviewCount()
        self.filteredCount.setText(previewCount)
        if previewCount == 0:
            self.infoLabel.setText(T("#Your downloads will be displayed here." if self.downloaderType == 0 and self.downloaderStatus == 0 else "#There are no matches for this filter."))
            self.stackedWidget.setCurrentIndex(0)
        else:
            self.stackedWidget.setCurrentIndex(1)

    def updateFilter(self):
        self.downloaderType = self.typeFilter.currentIndex()
        self.downloaderStatus = self.statusFilter.currentIndex()
        for downloaderId in self.previewItems:
            self.setPreviewHidden(downloaderId, not self.filterPreview(downloaderId))
        self.showPreviewCount()

    def getFilteredPreviewCount(self):
        return sum(0 if item.isHidden() else 1 for item in self.previewItems.values())

    def filterPreview(self, downloaderId):
        downloader = DownloadManager.get(downloaderId)
        return self._filterType(downloader) and self._filterStatus(downloader)

    def _filterType(self, downloader):
        if self.downloaderType == 0:
            return True
        elif self.downloaderType == 1:
            return downloader.setup.downloadInfo.type.isStream()
        elif self.downloaderType == 2:
            return downloader.setup.downloadInfo.type.isVideo()
        else:
            return downloader.setup.downloadInfo.type.isClip()

    def _filterStatus(self, downloader):
        if self.downloaderStatus == 0:
            return True
        elif self.downloaderStatus == 1:
            return downloader.isRunning()
        elif self.downloaderStatus == 2:
            return downloader.isFinished()
        elif self.downloaderStatus == 3:
            return downloader.isFinished() and downloader.status.terminateState.isFalse()
        elif self.downloaderStatus == 4:
            return downloader.isFinished() and downloader.status.terminateState.isTrue() and downloader.status.getError() != None
        else:
            return downloader.isFinished() and downloader.status.terminateState.isTrue() and downloader.status.getError() == None

    def openProgressWindow(self, item):
        if item.widget.isEnabled():
            self.progressWindowRequested.emit(item.widget.downloaderId)

    def showDownloadCompleteActionInfo(self):
        self.info("information", "#When all downloads are complete, it will perform the selected action.\nA warning notification will be displayed for a period of time so that the operation can be canceled.\nWhen the time expires, the action will be performed.")

    def restrictionsUpdated(self):
        restrictionsFound = []
        for downloader in DownloadManager.getRunningDownloaders():
            downloadInfo = downloader.setup.downloadInfo
            try:
                ContentManager.ContentManager.checkRestrictions(downloadInfo.videoData, user=DB.account.user)
            except ContentManager.Exceptions.RestrictedContent as e:
                downloader.abort(e)
                restrictionsFound.append(downloadInfo)
        if len(restrictionsFound) != 0:
            infoText = T("#Some content has been restricted.\nTerminating restricted downloads.")
            contentInfo = "\n".join(self.getContentInfoString(string) for string in restrictionsFound)
            self.info("warning", f"{infoText}\n\n{contentInfo}")

    def getContentInfoString(self, downloadInfo):
        if downloadInfo.type.isStream():
            channel = downloadInfo.videoData.broadcaster
        elif downloadInfo.type.isVideo():
            channel = downloadInfo.videoData.owner
        else:
            channel = downloadInfo.videoData.broadcaster
        return f"[{channel.displayName}] [{T(downloadInfo.type.toString())}] {downloadInfo.videoData.title}"