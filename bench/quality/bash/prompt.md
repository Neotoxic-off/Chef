Write a Bash script `backup.sh DIR DEST` that creates `DEST/<basename of DIR>-YYYYmmdd-HHMMSS.tar.gz` and keeps only the 7 newest backups of that directory in DEST. Missing arguments, a missing DIR or an unwritable DEST exit 2 with a message on stderr; a failed archive exits 1 and leaves no partial file.

Work autonomously: nobody will answer questions.
