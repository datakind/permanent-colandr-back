#!flask/bin/python
from app import app
import os

# extra_dirs = ['app/templates',]
# extra_files = extra_dirs[:]
# for extra_dir in extra_dirs:
#     for dirname, dirs, files in os.walk(extra_dir):
#         for filename in files:
#             filename = os.path.join(dirname, filename)
#             if os.path.isfile(filename):
#                 extra_files.append(filename)
#                 print filename


if __name__ == '__main__':
	# app.run(TEMPLATES_AUTO_RELOAD = True)

	app.run(host='localhost', port=5001,debug=True)

# app.run(extra_files=extra_files)

	# app.run(debug=True)
