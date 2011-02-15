#!/usr/bin/env python

import fuse
import stat
import errno
import os
from fuse import Fuse
from os.path import split, abspath, isfile, join

# setup logging

def log(s):	# by default do nothing
	pass
	
def logfn(fn):	# NOP-decorator:
	return fn

def log_exception(s=None):
	pass

if 'FSLISTVIEW_LOG' in os.environ:
	log_name  = 'fslistview.%d.log' % (os.getpid())
	directory =  os.environ['FSLISTVIEW_LOG']
	if not directory:
		directory = 'tmp'

	path = join(directory, log_name)
	print("fslistview: logging to " + path)
	f = open(path, 'w')

	def log(s):
		f.write(s + '\n')
		f.flush();

	def log_exception(info="exception"):
		import traceback
		log(info)
		traceback.print_exc(file=f)


	if 'FSLISTVIEW_LOG_FUNCTIONS' in os.environ:
		print("fslistview: logging all function calls [debug]")
		def logfn(fn):
			def wrapper(*args, **kwargs):
				f.write("%s(%r, %r)\n" % (fn.__name__, args, kwargs))
				f.flush()
				try:
					return fn(*args, **kwargs)
				except:
					log_exception(fn.__name__)
					raise

			return wrapper
else:
	print("fslistview: logging disabled")



READ_ONLY_PERM = \
	stat.S_IRUSR | stat.S_IXUSR | \
	stat.S_IRGRP | stat.S_IXGRP | \
	stat.S_IROTH | stat.S_IXOTH

class FileList(object):
	"List of files. Support renaming and removing real files."

	def __init__(self, path, basedir):
		self.path	= path
		self.basedir	= basedir
		self.list_stat	= None
		self.files	= {}
		self.counters	= {}
		self.reload()

	def reload(self):
		now = os.stat(self.path)
		if self.list_stat != now:
			self._load_list()
			self.list_stat = now

	def __len__(self):
		return len(self.files)

	def _preprocess_path(self, path):
		tmp = path
		if (self.basedir):
			tmp = join(self.basedir, path)

		tmp = os.path.expanduser(tmp)
		tmp = os.path.abspath(tmp)
		return tmp

	def _is_path_valid(self, path):
		return isfile(path)

	def _load_list(self):
		self.counters = {}
		self.files = {}
		for line in open(self.path, 'r'):
			line = line.strip()
			if not line:
				# skip empty lines
				break
			elif line[0] == '#':
				# skip comments
				break

			line = self._preprocess_path(line)
			if self._is_path_valid(line):
				print("entry: " + line)

				dir, file = split(line)
				self._set_file(file, line)
		pass

	def _set_file(self, file, real_path):
		if file in self.files:
			# repeated name, append number
			n    = self.counters.get(file, 0)
			name, ext = os.path.splitext(file)
			name = "%s {%d}%s" % (name, n+1, ext)

			self.counters[file] = n + 1
		else:
			name = file

		self.files[name] = real_path


	def __getitem__(self, key):
		return self.files[key]


	def __iter__(self):
		return iter(self.files)


	def rename(self, name1, name2):
		if name1 == name2:
			return

		path1 = self[name1]
		dir, _ = split(path1)
		path2 = join(dir, name2)	# replace file part

		os.rename(path1, path2)		# do the job

		del self.files[name1]		# update list
		self._set_file(name2, path2)


	def remove(self, name):
		path = self[name]
		os.remove(path)
		del self.files[name]


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
				FileProxy.__init__(self2, self, *args, **kwargs)
		
		self.file_class = Wrapper
		self.lists = {}

		import time
		self.timestamp = int(time.time())


	def set_lists(self, lists):
		self.lists = {}
		for L in lists:
			_, name = split(L.path)
			if name[0] != '/':
				name = '/' + name

			self.lists[name] = L

	
	def _vpath_to_real_path(self, path):
		dir, file = split(path)
		try:
			return self.lists[dir][file]
		except KeyError:
			err = IOError()
			err.errno = errno.ENOENT
			raise err


	@logfn
	def readdir(self, path, offset):
		if path == '/':
			# enumerate of lists
			for name in self.lists:
				d = fuse.Direntry(name[1:])
				d.type = stat.S_IFDIR
				yield d
		else:
			# numerate given list
			try:
				ls = self.lists[path]
			except KeyError:
				err = IOError()
				err.errno = errno.ENOENT
				raise err

			for path in ls:
				name = split(path)[-1]
				d = fuse.Direntry(name)
				d.type = stat.S_IFREG
				yield d

	@logfn
	def unlink(self, path):
		dir, file = split(path)
		ls = self.lists[dir]
		ls.remove(file)

	@logfn
	def rename(self, path1, path2):
		dir1, file1	= split(path1)
		dir2, file2	= split(path2)

		if dir1 != dir2:
			return -errno.EINVAL

		try:
			ls = self.lists[dir1]
		except KeyError:
			return -errno.ENOENT

		if file1 != file2:
			ls.rename(file1, file2)

	
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
			st.st_atime	= self.timestamp
			st.st_mtime	= self.timestamp
			st.st_ctime	= self.timestamp
			return st
		elif path in self.lists:
			L = self.lists[path]
			L.reload()
			st = fuse.Stat()
			st.st_ino	= 0
			st.st_dev	= 0
			st.st_blksize	= 4096
			st.st_mode	= stat.S_IFDIR | READ_ONLY_PERM
			st.st_nlink	= 1
			st.st_uid	= 0
			st.st_gid	= 0
			st.st_rdev	= None
			st.st_size	= len(L)
			st.st_blocks	= 0
			if L.list_stat:
				st.st_atime	= L.list_stat.st_atime
				st.st_mtime	= L.list_stat.st_mtime
				st.st_ctime	= L.list_stat.st_ctime
			else:
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
	import optparse
	import sys

	# parse arguments
	parser = optparse.OptionParser()
	parser.add_option(
		"-b", "--basedir",
		dest="basedir",
		help="base dir for next file"
	)

	def parse_file(option, opt, value, parser):
		item = (parser.values.basedir, value)
		if parser.values.files is None:
			parser.values.files = [item]
		else:
			parser.values.files.append(item)

		parser.values.basedir = None	# reset basedir

	parser.add_option(
		"-f", "--file",
		dest="files",
		type="string",
		help="name of file with list",
		action="callback",
		callback=parse_file
	)

	options, args = parser.parse_args(sys.argv)

	# load file lists
	lists = []
	if options.files:
		for basedir, path in options.files:
			if not basedir:
				basedir = None

			print("loading list from %s..." % path)
			L = FileList(path, basedir)
			lists.append(L)
	else:
		parser.error("at least one -f/--file option is required")

	# FUSE init
	print("starting FUSE...")
	
	fuse.fuse_python_api = (0, 2)

	server = FSFileList()
	server.multithreaded = False
	server.set_lists(lists)

	server.parse(args, errex=1)
	server.main()

	print("done")


if __name__ == '__main__':
	main()

