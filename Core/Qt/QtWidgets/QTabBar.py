from PyQt5 import QtCore, QtWidgets


class _QTabBar(QtWidgets.QTabBar):
    def isTabBarHorizontal(self):
        return self.parent().tabPosition() < 2

    def tabSizeHint(self, index):
        if self.isTabBarHorizontal():
            width = min(int(self.parent().width() / self.count()), 200)
            height = super().tabSizeHint(index).height() + 10
        else:
            width = super().tabSizeHint(index).height()
            height = super().tabSizeHint(index).width() + 50
        return QtCore.QSize(width, height)
QtWidgets.QTabBar = _QTabBar #Direct Class Patch - [Warning] Does not affect embedded objects (Use with caution)