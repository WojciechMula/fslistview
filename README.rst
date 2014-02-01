fslistview
==========

.. contents:: Contents


Introduciton
-----------------------------------

**fslistview** is a file system using FUSE__ that allows to expose
flat list of files in a single virtual directory. Only files are
considered --- directories, links, fifos, etc. are skipped.  If file
name repeat, then some number is appended.

It's possible to mount several lists at once, each list is represented
as subdirectory.  If a file containing list has been changed, then
list is reloaded.

**fslistview** allows limited operations set on real files:

* read content of file
* remove file

__ http://fuse.sourceforge.net/


File lists
-----------------------------------

Rules:

* each line in file list is a path; special symbol ``~`` (tilde)
  is expanded
* empty lines are skipped
* lines beginning with ``#`` are considered as comments
* paths must be in absolute form
* all relative paths could be converted to absolute 
  if option ``--base-dir`` is set


Command line
-----------------------------------

::

	fslistview.py [progam options] mount-point [FUSE options]

Where program options are:

-b DIR			base directory for **next list**
--base-dir=DIR		long version of -b

-f FILE			file containting list
--file=FILE		long version of -f


These options can be passed as many times as it's needed,
for example:

::

	fslistview.py -b /mnt/music -f latest-cd.list -f duplicated-documents.list -b /mnt/data/backups -f old-backups.list mount-point

This command will mount three file lists:

* ``latest-cd.list`` [relative paths are bind to ``/mnt/music``]
* ``duplicated-documents.list``
* ``old-backups.list`` [reloaded paths are bind to ``/mnt/data/backups``]


Environment variable
-----------------------------------

Variable ``FSLISTVIEW_LOG`` should be used only for debugging purposes.
This variable have to point a writable directory (for example ``/tmp/``),
where file ``fslistview.{PID}.log`` is created and filled with information
about all functions calls and possible errors (exceptions).


License
-----------------------------------

Program is licensed under simplfied **BSD**
