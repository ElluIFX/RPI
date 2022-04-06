import requests
import os
from bypy import ByPy
from time import sleep, time, localtime, asctime, strftime
from urllib.parse import quote, unquote, urlencode
import _thread

apikey = 'SCT73826TdGSa1RyhZx068bEVQKFftBq5'
post_target = f'https://sctapi.ftqq.com/{apikey}.send?title='+'{}'
post_target_with_desp = post_target+'&desp={}'
updating = False
dir = '/home/pi/motion/'
last_update_time = 0
last_list = []
new_files = []
bp = ByPy()


def check_motion_state():
    global last_list, updating, last_update_time, new_files

    if updating and time()-last_update_time > 70:
        updating = False
        text = '> ### File list:\r\n'
        for i in range(len(new_files)):
            text += '> '+f'{i+1}' + '. ' + new_files[i] + '\r\n'
        text = quote(text)
        requests.post(post_target_with_desp.format('Motion Detect Stopped',
                      'Added {} new files: \r\n\r\n {}'.format(len(new_files), str(text))))
        print(f'{asctime(localtime(time()))}: Motion Detect Stopped')
        new_files = []
        try:
            # _thread.start_new_thread(sync_with_cloud, ())
            sync_with_cloud()
        except Exception as e:
            print(e)

        return

    file_list = os.listdir(dir)
    # file_list.remove('motion.log')
    # file_list.remove('lastsnap.jpg')
    # for f in file_list:
    #     if not f.startswith('M'):
    #         file_list.remove(f)

    if len(last_list) == 0:
        last_list = file_list
    if len(file_list) == len(last_list):
        return

    if not updating:
        updating = True
        last_update_time = time()
        new_files = []
        requests.post(post_target_with_desp.format(
            'Motion Detect Started', f'{asctime(localtime(time()))}'))
        print(f'{asctime(localtime(time()))}: Motion Detect Started')
        return
    else:
        # print(".", end='')
        new_files += [f for f in file_list if f not in last_list]
        last_list = file_list
        last_update_time = time()
        return


def zip_and_upload():
    timeNow = f'{strftime("%Y-%m-%d-%H-%M-%S", localtime())}'
    fileName = f'{timeNow}_motion.tar.gz'
    print(f'{asctime(localtime(time()))}: Start zipping files...')
    os.system(
        f'cd /home/pi && tar -czvf {fileName} motion  >/dev/null 2>&1')
    print(f'{asctime(localtime(time()))}: Start uploading files...')
    bp.upload(localpath=f'/home/pi/{fileName}', remotepath='/motion')
    os.system(f'rm -f /home/pi/{fileName} >/dev/null 2>&1')
    last_list = []
    print(f'{asctime(localtime(time()))}: Uploading files finished.')


def sync_with_cloud():
    print(f'{asctime(localtime(time()))}: Start syncing files...')
    bp.syncup(localdir='/home/pi/motion', remotedir='/motion')
    # delete local files
    # os.system(f'rm -f /home/pi/motion/M* >/dev/null 2>&1')
    # last_list = []
    print(f'{asctime(localtime(time()))}: Sync files finished.')

if __name__ == '__main__':
    url = post_target_with_desp.format(
        'Raspberry Pi Online', f'{asctime(localtime(time()))}')
    response = requests.post(url)
    print(f'{asctime(localtime(time()))}: Raspberry Pi Online')
    # print(response.json())
    while True:
        sleep(1)
        try:
            check_motion_state()
            # zip_and_upload()
            # exit()
        except Exception as e:
            print(e)
