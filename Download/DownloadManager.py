from Core.App import App
from Download.Downloader.Engine.Engine import TwitchDownloader

from PyQt5 import QtCore


class Exceptions:
    class DownloaderCreationDisabled(Exception):
        def __str__(self):
            return "Downloader Creation Disabled"


class _DownloadManager(QtCore.QObject):
    createdSignal = QtCore.pyqtSignal(object)
    destroyedSignal = QtCore.pyqtSignal(object)
    startedSignal = QtCore.pyqtSignal(object)
    completedSignal = QtCore.pyqtSignal(object)
    runningCountChangedSignal = QtCore.pyqtSignal(int)

    def __init__(self, parent=None):
        super(_DownloadManager, self).__init__(parent=parent)
        self.downloaders = {}
        self.runningDownloaders = []
        self._downloaderCreationEnabled = False
        self._representativeDownloader = None

    def setDownloaderCreationEnabled(self, enabled):
        self._downloaderCreationEnabled = enabled

    def onStart(self, downloader):
        if len(self.runningDownloaders) == 0:
            self.showDownloaderProgress(downloader)
        elif len(self.runningDownloaders) == 1:
            self.hideDownloaderProgress(complete=False)
        self.runningDownloaders.append(downloader)
        self.runningCountChangedSignal.emit(len(self.runningDownloaders))
        self.startedSignal.emit(downloader.getId())

    def onFinish(self, downloader):
        self.runningDownloaders.remove(downloader)
        if len(self.runningDownloaders) == 0:
            self.hideDownloaderProgress(complete=True)
        elif len(self.runningDownloaders) == 1:
            self.showDownloaderProgress(self.runningDownloaders[0])
        self.runningCountChangedSignal.emit(len(self.runningDownloaders))
        self.completedSignal.emit(downloader.getId())

    def showDownloaderProgress(self, downloader):
        self._representativeDownloader = downloader
        self._representativeDownloader.hasUpdate.connect(self.handleRepresentativeDownloader)
        App.taskbar.show(indeterminate=self._representativeDownloader.setup.downloadInfo.type.isStream())
        self._representativeDownloader.hasUpdate.emit()

    def hideDownloaderProgress(self, complete):
        self._representativeDownloader.hasUpdate.disconnect(self.handleRepresentativeDownloader)
        self._representativeDownloader = None
        if complete:
            App.taskbar.complete()
        else:
            App.taskbar.hide()

    def create(self, downloadInfo):
        if self._downloaderCreationEnabled:
            downloader = TwitchDownloader(downloadInfo, parent=self)
            downloader.started.connect(self.onStart)
            downloader.finished.connect(self.onFinish)
            downloaderId = downloader.getId()
            self.downloaders[downloaderId] = downloader
            self.createdSignal.emit(downloaderId)
            return downloaderId
        else:
            raise Exceptions.DownloaderCreationDisabled

    def get(self, downloaderId):
        return self.downloaders[downloaderId]

    def cancelAll(self):
        for downloader in self.downloaders.values():
            downloader.cancel()

    def waitAll(self):
        for downloader in self.downloaders.values():
            downloader.wait()

    def remove(self, downloaderId):
        self.downloaders[downloaderId].cancel()
        self.downloaders[downloaderId].wait()
        self.downloaders.pop(downloaderId).setParent(None)
        self.destroyedSignal.emit(downloaderId)

    def getRunningDownloaders(self):
        return self.runningDownloaders

    def isDownloaderRunning(self):
        return len(self.getRunningDownloaders()) != 0

    def isShuttingDown(self):
        return not any(downloader.status.terminateState.isFalse() for downloader in self.runningDownloaders)

    def handleRepresentativeDownloader(self):
        if self._representativeDownloader.setup.downloadInfo.type.isStream():
            self.handleStreamProgress(self._representativeDownloader)
        elif self._representativeDownloader.setup.downloadInfo.type.isVideo():
            self.handleVideoProgress(self._representativeDownloader)
        else:
            self.handleClipProgress(self._representativeDownloader)

    def handleStreamProgress(self, downloader):
        status = downloader.status
        if not status.terminateState.isFalse():
            App.taskbar.stop()

    def handleVideoProgress(self, downloader):
        status = downloader.status
        progress = downloader.progress
        if status.isEncoding():
            App.taskbar.setValue(progress.timeProgress)
        else:
            App.taskbar.setValue(progress.fileProgress)
        if not status.terminateState.isFalse():
            App.taskbar.stop()
        elif not status.pauseState.isFalse() or status.isWaiting() or status.isUpdating() or status.isEncoding():
            App.taskbar.pause()

    def handleClipProgress(self, downloader):
        progress = downloader.progress
        App.taskbar.setValue(progress.sizeProgress)

DownloadManager = _DownloadManager()