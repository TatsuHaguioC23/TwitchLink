from .Config import Config

from Core.App import App
from Services.Utils.OSUtils import OSUtils

import os
import ctypes
import tempfile


class SafeTempDirectory:
    def __init__(self, directory, dirPrefix, keyFileDir):
        self.directory = tempfile.TemporaryDirectory(dir=directory, prefix=dirPrefix)
        self.name = self.directory.name
        ctypes.windll.kernel32.SetFileAttributesW(self.name, 2)
        self.file = tempfile.NamedTemporaryFile(dir=keyFileDir, mode="w", delete=False)
        self.file.write(self.name)
        self.file.flush()

    def cleanup(self):
        self.directory.cleanup()
        self.file.close()
        OSUtils.removeFile(self.file.name)


class _TempManager:
    def __init__(self):
        try:
            OSUtils.createDirectory(Config.TEMP_LIST_DIRECTORY)
            self.cleanup()
        except:
            pass

    def cleanup(self):
        files = os.listdir(Config.TEMP_LIST_DIRECTORY)
        if len(files) == 0:
            return
        else:
            App.logger.info("Cleaning up temp files.")
        for filename in files:
            path = OSUtils.joinPath(Config.TEMP_LIST_DIRECTORY, filename)
            try:
                self.cleanTempDirKeyFile(path)
            except Exception as e:
                App.logger.exception(e)

    def cleanTempDirKeyFile(self, tempDirKeyFile):
        if OSUtils.isFile(tempDirKeyFile):
            with open(tempDirKeyFile) as file:
                tempDir = file.read()
                if OSUtils.isDirectory(tempDir):
                    App.logger.info(f"Removing temp directory: {tempDir}")
                    OSUtils.removeDirectory(tempDir)
            OSUtils.removeFile(tempDirKeyFile)

    def createTempDirectory(self, directory):
        return SafeTempDirectory(directory, dirPrefix=Config.DIRECTORY_PREFIX, keyFileDir=Config.TEMP_LIST_DIRECTORY)

TempManager = _TempManager()