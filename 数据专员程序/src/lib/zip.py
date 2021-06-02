
import zipfile


# 解压缩文件
def unzip(file, unzip_path=None):
    zip = zipfile.ZipFile(file)
    zip.extractall(unzip_path)
    if unzip_path is not None:
        return [unzip_path.joinpath(file) for file in zip.namelist()]
    else:
        return zip.namelist()
