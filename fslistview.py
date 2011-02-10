#!/usr/bin/env python

import fuse
import stat
import errno
import os
from fuse import Fuse
from os.path import split, abspath, isfile

f = open('/home/wojtek/log', 'w')
def log(s):
	f.write(s + '\n')
	f.flush();

def logfn(fn):
	def wrapper(*args, **kwargs):
		f.write("%s(%r, %r)\n" % (fn.__name__, args, kwargs))
		f.flush()
		return fn(*args, **kwargs)

	return wrapper

def log_exception(info="!!!error"):
	import traceback
	log(info)
	traceback.print_exc(file=f)

READ_ONLY_PERM = \
	stat.S_IRUSR | stat.S_IXUSR | \
	stat.S_IRGRP | stat.S_IXGRP | \
	stat.S_IROTH | stat.S_IXOTH

class FileProxy(object):

	@logfn
	def __init__(self, self2, *args, **kwargs):
		self.fs = self2
		path = args[0]
		self.file = open(self.fs._vpath_to_real_path(path), 'r')
		self.fd = self.file.fileno()
		self.direct_io = False
		self.keep_cache = False

	@logfn
	def open(self, *args, **kwargs):
		pass

	@logfn
	def read(self, length, offset):
		self.file.seek(offset)
		return self.file.read(length)

	@logfn
	def write(self, buf, offset):
		"NOT IMPLEMENTED"
		return -errno.ENOSYS

	@logfn
	def fgetattr(self):
		log("%r" % os.fstat(self.fd))

		stfile = os.fstat(self.fd)
		#stfile.st_mode	= stat.S_IFREG | READ_ONLY_PERM
		return stfile

		st = fuse.Stat()

		st.st_ino	= stfile.st_ino
		st.st_dev	= stfile.st_dev
		st.st_blksize	= stfile.st_blksize
		st.st_mode	= stfile.st_mode
		st.st_nlink	= stfile.st_nlink
		st.st_uid	= stfile.st_uid
		st.st_gid	= stfile.st_gid
		st.st_rdev	= stfile.st_rdev
		st.st_size	= stfile.st_size
		st.st_blocks	= stfile.st_blocks
		st.st_atime	= stfile.st_atime
		st.st_mtime	= stfile.st_mtime
		st.st_ctime	= stfile.st_ctime

		return st

	@logfn
	def ftruncate(self, len):
		"NOT IMPLEMENTED"
		return -errno.ENOSYS

	@logfn
	def flush(self):
		pass

	@logfn
	def release(self):
		self.file.close()
		
	@logfn
	def fsync(self, fdatasync):
		"NOT IMPLEMENTED"
		return -errno.ENOSYS

	@logfn
	def lock(self, *args, **kwargs):
		pass


class FSFileList(Fuse):
	
	@logfn
	def __init__(self, *args, **kwargs):

		Fuse.__init__(self, *args, **kwargs)

		class Wrapper(FileProxy):
			def __init__(self2, *args, **kwargs):
				log("Wrapper::init(%r, %r, %r, %r)" % (self2, self, args, kwargs))
				try:
					FileProxy.__init__(self2, self, *args, **kwargs)
				except:
					log_exception()
		
		self.file_class = Wrapper

		# lists
		self.lists = {}
		self._load_list('/home/wojtek/list')
		self._load_list('/home/wojtek/mp3')

	def _vpath_to_real_path(self, path):
		dir, file = os.path.split(path)
		try:
			return self.lists[dir[1:]][file]
		except KeyError:
			err = IOError()
			err.errno = errno.ENOENT
			raise err

	def _preprocess_path(self, path):
		tmp = os.path.expanduser(path)
		tmp = os.path.abspath(tmp)
		return tmp

	def _is_path_valid(self, path):
		return True or isfile(path)

	def _load_list(self, path):
		L = {}
		for line in open(path, "r"):
			line = line.rstrip()
			if not line:
				# skip empty lines
				break
			elif line[0] == '#':
				# skip comments
				break

			line = self._preprocess_path(line)
			if self._is_path_valid(line):
				log("entry:" + line)

				dir, file = os.path.split(line)
				L[file] = line

			
		directory = split(path)[-1]
		self.lists[directory] = L

	@logfn
	def readdir(self, path, offset):
		if path == '/':
			# enumerate of lists
			for name in self.lists:
				d = fuse.Direntry(name)
				d.type = stat.S_IFDIR
				yield d
		else:
			# numerate given list
			directory = split(path)[-1]
			for path in self.lists[directory]:
				name = split(path)[-1]
				d = fuse.Direntry(name)
				d.type = stat.S_IFREG
				yield d

	@logfn
	def unlink(self, path):
		

	@logfn
	def getattr(self, path):
		if path == "/":
			st = fuse.Stat()
			st.st_ino	= 0
			st.st_dev	= 0
			st.st_blksize	= 4096
			st.st_mode	= stat.S_IFDIR | READ_ONLY_PERM
			st.st_nlink	= 1
			st.st_uid	= 0
			st.st_gid	= 0
			st.st_rdev	= None
			st.st_size	= len(self.lists)
			st.st_blocks	= 0
			st.st_atime	= 0
			st.st_mtime	= 0
			st.st_ctime	= 0
			return st
		elif path[1:] in self.lists:
			st = fuse.Stat()
			st.st_ino	= 0
			st.st_dev	= 0
			st.st_blksize	= 4096
			st.st_mode	= stat.S_IFDIR | READ_ONLY_PERM
			st.st_nlink	= 1
			st.st_uid	= 0
			st.st_gid	= 0
			st.st_rdev	= None
			st.st_size	= len(self.lists[path[1:]])
			st.st_blocks	= 0
			st.st_atime	= 0
			st.st_mtime	= 0
			st.st_ctime	= 0
			return st
		else:
			path = self._vpath_to_real_path(path)
			stfile = os.lstat(path)

			st = fuse.Stat()

			st.st_ino	= stfile.st_ino
			st.st_dev	= stfile.st_dev
			st.st_blksize	= stfile.st_blksize
			st.st_mode	= stfile.st_mode
			st.st_nlink	= stfile.st_nlink
			st.st_uid	= stfile.st_uid
			st.st_gid	= stfile.st_gid
			st.st_rdev	= stfile.st_rdev
			st.st_size	= stfile.st_size
			st.st_blocks	= stfile.st_blocks
			st.st_atime	= stfile.st_atime
			st.st_mtime	= stfile.st_mtime
			st.st_ctime	= stfile.st_ctime
			return st


def main():
	fuse.fuse_python_api = (0, 2)

	server = FSFileList()
	server.multithreaded = False
	server.parse(errex=1)
	server.main()


if __name__ == '__main__':
	main()

