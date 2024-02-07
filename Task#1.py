import pytest
import random, string
import yaml
from datetime import datetime
from sshcmd import ssh_checkout, ssh_getout, upload_files, download_files, ssh_checkout_negative
import subprocess

# dpkg -l | grep 7zip - команда для поиска пакета в системе (первая часть выдает просто список всех пакетов,
# вторая - ищем конкретный пакет)
# dpkg -r 7zip-full -удаление пакета
# su <name_user> - команда для перехода от юзера к юзеру
# sudo dpkg -i ./p7zip-full.ded - установка 7z


with open('config.yaml') as f:
    # читаем документ YAML
    data = yaml.safe_load(f)


def checkout(comand, text):
    result = subprocess.run(comand, shell=True, stdout=subprocess.PIPE, encoding='utf-8')
    print(result.stdout)
    if text in result.stdout and result.returncode == 0:
        return True
    else:
        return False


@pytest.fixture()
def make_folders():
    # Фикстура создания папки (параметры подтягиваются из config файла)
    return checkout(f"mkdir {data['folder_in']} {data['folder_in']} {data['folder_ext']} {data['folder_ext2']}", "")

@pytest.fixture()
def clear_folders():
    # Фикстура очистки папки (параметры подтягиваются из config файла)
    return checkout(f"rm -rf {data['folder_in']} {data['folder_in']} {data['folder_ext']} {data['folder_ext2']}/*", "")

@pytest.fixture()
def make_files():
    # Фикстура создания файлов в папке с заданным размером (параметры подтягиваются из config файла)
    list_of_files = []
    for i in range(data["count"]):
        filename = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        if checkout(f"cd {data['folder_in']}; dd if=/dev/urandom of={filename} bs={data['bs']} count=1 iflag=fullblock", ""):
            list_of_files.append(filename)
    return list_of_files

@pytest.fixture()
def make_subfolder():
    # Фикстура для генерирования названия подпапок
    testfilename = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    subfoldername = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    # string.ascii_uppercase, string.digits - коллекции всех фукв и цифр
    if not checkout("cd {}; mkdir {}".format(data["folder_in"], subfoldername), ""):
        return None, None
    if not checkout(f"cd {data['folder_in']}/{subfoldername}; dd if=/dev/urandom of={testfilename} bs=1M count=1 iflag=fullblock", ""):
        return subfoldername, None
    else:
        return subfoldername, testfilename

@pytest.fixture(autouse=True)
def print_time():
    # Фикстура для измерения времени
    print(f"Start: {datetime.now().strftime('%H:%M:%S.%f')}")
    yield
    print(f"Finish: {datetime.now().strftime('%H:%M:%S.%f')}")

@pytest.fixture()
def add_log_file():
    # Task#1
    #функция логирования
    with open('stat.txt', 'a') as f:
        yield 0
        time = f"Time status: {datetime.now().strftime('%H:%M:%S.%f')}"
        print(time)
        number_file_in_folder = data["count"]
        size_of_file = data["bs"]
        # Task#2
        info_load_of_process = subprocess.run(f"cat /proc/loadavg", shell=True, stdout=subprocess.PIPE, encoding='utf-8')
        f.write(f"{time} - Number files: {number_file_in_folder} - Size of file: {size_of_file} - {info_load_of_process}\n")

def find_subprocess(path: str, text: str):
    result = subprocess.run(path, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')
    lst = result.stdout.split("\n") + result.stderr.split("\n")

    print(text in lst)
    if text in lst:
        return True
    else:
        return False

class Test_positiv:
    def test_step0(self):
        res = []
        upload_files("0.0.0.0", "user2", "11", "tests/p7zip-full.deb", "/home/user2/p7zip-full.deb")
        res.append(ssh_checkout("0.0.0.0", "user2", "11", "echo '11' | sudo -S dpkg -i /home/user2/p7zip-full.deb",
                                "Setting up"))
        res.append(ssh_checkout("0.0.0.0", "user2", "11", "echo '11' | sudo -S dpkg -s p7zip-full",
                                "Status: install ok installed"))
        assert all(res)

    ########
    def test_step1_ssh(self, clear_folders, make_files, add_log_file):
        res1 = ssh_checkout(f"{data['host']}", f"{data['user_name']}", f"{data['passwd']}" ,f"cd {data['tst']}; 7z a {data['out']}/arx2", "Everything is 0k")
        res2 = ssh_checkout(f"{data['host']}", f"{data['user_name']}", f"{data['passwd']}", f"ls {data['out']}", "arx2.7z")
        assert res1 and res2, "test1 FAIL"

    def test_step2_ssh(self, clear_folders, make_files, add_log_file):
        res = []
        res.append(ssh_checkout(f"{data['host']}", f"{data['user_name']}", f"{data['passwd']}", f"cd {data['tst']}; 7z a {data['out']}/arx2", "Everything is 0k"))
        res.append(ssh_checkout(f"{data['host']}", f"{data['user_name']}", f"{data['passwd']}", f"cd {data['out']}; 7z e arx2.7z -o{data['folder1']} -y", "Everything is 0k"))

        for item in make_files:
            res.append(find_subprocess(f"ls {data['folder1']}", item))
        assert all(res), "test2 FAIL"

    def test_step3_ssh(self, add_log_file):
        assert ssh_checkout(f"{data['host']}", f"{data['user_name']}", f"{data['passwd']}", f"cd {data['out']}/out; 7z l arx2.7z", "1 files"), "test3 FAIL"

    def test_step4_ssh(self, add_log_file):
        # t: проверка целостности архива
        assert ssh_checkout(f"{data['host']}", f"{data['user_name']}",f"{data['passwd']}", f"cd {data['out']}/out; 7z t arx2.7z", 'Everything is Ok'), "test4 FAIL"

    def test_step5_ssh(self, add_log_file):
        assert ssh_checkout(f"{data['host']}", f"{data['user_name']}", f"{data['passwd']}", f"cd {data['out']}/out; 7z d arx2.7z", 'Everything is Ok'), "test5 FAIL"

    def test_step6_ssh(self, add_log_file):
        assert ssh_checkout(f"{data['host']}", f"{data['user_name']}", f"{data['passwd']}", f"cd {data['out']}/out; 7z u arx2.7z", 'Everything is Ok'), "test6 FAIL"

    def test_step7_ssh(self, clear_folders, make_files, add_log_file):
        ssh_checkout(f"{data['host']}", f"{data['user_name']}", f"{data['passwd']}", f"cd {data['tst']}; 7z a {data['out']}/arx2", "Everything is 0k")
        assert ssh_checkout(f"{data['host']}", f"{data['user_name']}", f"{data['passwd']}", f"cd {data['out']} && 7z x arx2.7z -o{data['folder1']}", 'Everything is Ok'), "test7 FAIL"

    ########

    # def test_step 8(self, clear_folders, make_files):
    #
    # # test8
    # res = []
    # for i in make_files:
    #     res.append(checkout("cd {}; 7z h {}}".format("args: data["folder_in"], i), text: "Everything is Ok"))
    #     hash = getout("cd {}; crc32 {}".format("args: data["folder_in"], i)).upper()
    #     res.append(checkout("cd {}; 7z h {}".format("args: data["folder_in"], i), hash))
    #     assert all(res), "test8 FAIL"
