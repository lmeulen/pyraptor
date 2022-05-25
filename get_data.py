import os
import shutil


cwd = os.getcwd()
print(f"Current working directory: {cwd}")

def mkdir_if_not_exists(name: str) -> None:
    """Create directory if not exists"""
    if not os.path.exists(name):
        os.makedirs(name)

src = '/Users/yunusskeete/Downloads/gtfs-3/'
dst = cwd + '/data/input/NL-gtfs/'

file_names = ['agency', 'calendar_dates', 'feed_info', 'routes', 'shapes', 'stop_times', 'stops', 'transfers', 'trips']
mkdir_if_not_exists(cwd + '/data/input')
mkdir_if_not_exists(dst)


for file_name in file_names:
    if not os.path.exists(dst + file_name + '.txt'):
        shutil.copyfile(src + file_name + '.txt', dst + file_name + '.txt')