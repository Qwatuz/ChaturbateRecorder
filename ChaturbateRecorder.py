import urllib.request, time, datetime, os, threading, sys, multiprocessing, signal, requests, configparser, re
from bs4 import BeautifulSoup
from contextlib import contextmanager
from livestreamer import Livestreamer

Config = configparser.ConfigParser()
Config.read(sys.path[0] + "/config.conf")
save_directory = Config.get('paths', 'save_directory')
wishlist = Config.get('paths', 'wishlist')
interval = int(Config.get('settings', 'checkInterval'))
genders = re.sub(' ', '', Config.get('settings', 'genders')).split(",")


class TimeoutException(Exception): pass

@contextmanager
def time_limit(seconds):
    def signal_handler(signum, frame):
        raise TimeoutException("Timed out!")

    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)


class checkForModels:
    def getModels(self):
        pages = []
        for gender in genders:
            for i in range(1, 50):
                pages.append([i, gender])
        p = multiprocessing.Pool(3)
        online = p.map(getOnlineModels, pages)
        p.terminate()
        return online

recording = []
def getOnlineModels(args):
    global lastPage
    MODELS = []
    page = args[0]
    gender = args[1]
    if page < lastPage[gender]:
        attempt = 1
        while attempt <= 3:
            with time_limit(8):
                try:
                    URL = "https://chaturbate.com/{gender}-cams/?page={page}".format(gender=gender.lower(), page=page)
                    result = requests.request('GET', URL)
                    result = result.text
                    soup = BeautifulSoup(result, 'lxml')
                    if lastPage[gender] == 100:
                        lastPage[gender] = int(soup.findAll('a', {'class': 'endless_page_link'})[-2].string)
                    if int(soup.findAll('li', {'class': 'active'})[1].string) == page:
                        LIST = soup.findAll('ul', {'class': 'list'})[0]
                        models = LIST.find_all('div', {'class': 'title'})
                        for model in models:
                            MODELS.append(model.find_all('a', href=True)[0].string.lower()[1:])
                    break
                except TimeoutException:
                    attempt = attempt + 1
    return MODELS

def startRecording(model):
    try:
        URL = "https://chaturbate.com/{}/".format(model)
        result = urllib.request.urlopen(URL)
        result = result.read().decode()
        for line in result.splitlines():
            if "m3u8" in line:
                stream = line.split("'")[1]
                break
        soup = BeautifulSoup(result, 'lxml')
        soup = soup.findAll('div', id="tabs_content_container")
        for line in str(soup).split():
            if 'Sex:' in line:
                gender = line.split("</dt><dd>")[1][:-5].lower()
        session = Livestreamer()
        session.set_option('http-headers', "referer=https://www.cam4.com/{}".format(model))
        streams = session.streams("hlsvariant://{}"
          .format(stream))
        stream = streams["best"]
        fd = stream.open()
        ts = time.time()
        st = datetime.datetime.fromtimestamp(ts).strftime("%d.%m.%Y_%H.%M.%S")
        if not os.path.exists("{path}/{model}_{gender}".format(path=save_directory, model=model, gender=gender)):
            os.makedirs("{path}/{model}_{gender}".format(path=save_directory, model=model, gender=gender))
        with open("{path}/{model}_{gender}/{st}_{model}_{gender}.mp4".format(path=save_directory, model=model, gender=gender,
                                                           st=st), 'wb') as f:
            recording.append(model)
            while True:
                try:
                    data = fd.read(1024)
                    f.write(data)
                except:
                    f.close()
                    recording.remove(model)
                    return

        if model in recording:
            recording.remove(model)
    except:
        if model in recording:
            recording.remove(model)


if __name__ == '__main__':
    AllowedGenders = ['female', 'male', 'trans', 'couple']
    genders = [a.lower() for a in genders]
    for gender in genders:
        if gender.lower() not in AllowedGenders:
            print(gender, "is not an acceptable gender, options are: female, male, trans, and couple - please correct your config file")
            exit()
    checker = checkForModels()
    print()
    sys.stdout.write("\033[F")
    while True:
        sys.stdout.write("\033[K")
        print("{} model(s) are being recorded. Getting list of online models now".format(len(recording)))
        sys.stdout.write("\033[K")
        print("the following models are being recorded: {}".format(recording), end="\r")
        lastPage = {'female': 100, 'couple': 100, 'trans': 100, 'male': 100}
        online = []
        online = checker.getModels()
        online = [ent for sublist in online for ent in sublist]
        online = list(set(online))
        with open(wishlist) as f:
            for model in f:
                models = model.split()
                for theModel in models:
                    if theModel.lower() in online and theModel.lower() not in recording:
                        thread = threading.Thread(target=startRecording, args=(theModel.lower(),))
                        thread.start()
        f.close()
        sys.stdout.write("\033[F")
        for i in range(interval, 0, -1):
            sys.stdout.write("\033[K")
            print("{} model(s) are being recorded. Next check in {} seconds".format(len(recording), i))
            sys.stdout.write("\033[K")
            print("the following models are being recorded: {}".format(recording), end="\r")
            time.sleep(1)
            sys.stdout.write("\033[F")
