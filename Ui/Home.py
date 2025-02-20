from Core.Ui import *
from Services.Messages import Messages
from Services.Twitch.Gql import TwitchGqlModels
from Search.Modes import SearchModes
from Search import ExternalPlaylist
from Download.DownloadInfo import DownloadInfo
from Download.DownloadManager import DownloadManager


class Home(QtWidgets.QWidget, UiFile.home):
    searchResultWindowRequested = QtCore.pyqtSignal(object)

    def __init__(self, parent=None):
        super(Home, self).__init__(parent=parent)
        self.appLogo.setMargin(10)
        self.appName.setText(Config.APP_NAME)
        self.smartSearchButton.clicked.connect(self.smartSearch)
        self.channelSearchButton.clicked.connect(self.searchChannel)
        self.videoClipSearchButton.clicked.connect(self.searchVideo)
        self.urlSearchButton.clicked.connect(self.searchUrl)
        self.copyright.setText(Config.getCopyrightInfo())

    def smartSearch(self):
        self.startSearch(SearchModes(SearchModes.UNKNOWN))

    def searchChannel(self):
        self.startSearch(SearchModes(SearchModes.CHANNEL))

    def searchVideo(self):
        self.startSearch(SearchModes(SearchModes.VIDEO))

    def searchUrl(self):
        self.startSearch(SearchModes(SearchModes.URL))

    def startSearch(self, mode):
        searchResult = Ui.Search(mode, parent=self).exec()
        if searchResult != False:
            if isinstance(searchResult, ExternalPlaylist.ExternalPlaylist):
                if searchResult.type.isStream():
                    data = TwitchGqlModels.Stream({"title": "Unknown Stream", "game": {"name": "Unknown"}, "broadcaster": {"login": "Unknown User"}})
                else:
                    data = TwitchGqlModels.Video({"title": "Unknown Video", "game": {"name": "Unknown"}, "owner": {"login": "Unknown User"}, "lengthSeconds": searchResult.totalSeconds})
                downloadInfo = Ui.DownloadMenu(DownloadInfo(data, searchResult), parent=self).exec()
                if downloadInfo != False:
                    try:
                        DownloadManager.create(downloadInfo)
                    except:
                        self.info(*Messages.INFO.ACTION_PERFORM_ERROR)
            else:
                self.searchResultWindowRequested.emit(searchResult)