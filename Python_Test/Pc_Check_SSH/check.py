# coding = utf-8

"""
@author: DevinX

@file: check.py

@time: 2019/9/23 18:11

@desc: 批量ssh链接服务器 返回命令执行反馈 写入文件/发送邮件

"""
import paramiko

class SSHParamiko(object):

    err = "argument passwd or rsafile can not be None"

    def __init__(self, host, port, user, passwd=None, rsafile=None):
        self.h = host
        self.p = port
        self.u = user
        self.w = passwd
        self.rsa = rsafile

    def _connect(self):
        if self.w:
            return self.pwd_connect()
        elif self.rsa:
            return self.rsa_connect()
        else:
            raise ConnectionError(self.err)

    def _transfer(self):
        if self.w:
            return self.pwd_transfer()
        elif self.rsa:
            return self.rsa_transfer()
        else:
            raise ConnectionError(self.err)

    def pwd_connect(self):
        conn = paramiko.SSHClient()
        conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        conn.connect(self.h, self.p, self.u, self.w)
        return conn

    def rsa_connect(self):
        pkey = paramiko.RSAKey.from_private_key_file(self.rsa)
        conn = paramiko.SSHClient()
        conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        conn.connect(hostname=self.h, port=self.p, username=self.u, pkey=pkey)
        return conn

    def pwd_transfer(self):
        transport = paramiko.Transport(self.h, self.p)
        transport.connect(username=self.u, password=self.w)
        sftp = paramiko.SFTPClient.from_transport(transport)
        return sftp, transport

    def rsa_transfer(self):
        pkey = paramiko.RSAKey.from_private_key_file(self.rsa)
        transport = paramiko.Transport(self.h, self.p)
        transport.connect(username=self.u, pkey=pkey)
        sftp = paramiko.SFTPClient.from_transport(transport)
        return sftp, transport

    def run_cmd(self, cmd):
        conn = self._connect()
        stdin, stdout, stderr = conn.exec_command(cmd)
        code = stdout.channel.recv_exit_status()
        stdout, stderr = stdout.read(), stderr.read()
        conn.close()
        if not stderr:
            return code, stdout.decode()
        else:
            return code, stderr.decode()

    def get_file(self, remote, local):
        sftp, conn = self._transfer()
        sftp.get(remote, local)
        conn.close()

    def put_file(self, local, remote):
        sftp, conn = self._transfer()
        sftp.put(local, remote)
        conn.close()


from concurrent.futures import ThreadPoolExecutor

class AllRun(object):
    def __init__(self, ssh_objs, cmds, max_worker=50):
        self.objs = [o for o in ssh_objs]
        self.cmds = [c for c in cmds]
        # print('[+]',self.objs,self.cmds)
        self.max_worker = max_worker  # 最大并发线程数

        self.success_hosts = []       # 存放成功机器数目
        self.failed_hosts = []        # 存放失败的机器IP
        self.mode = None
        self.func = None

    def serial_exec(self, obj):
        """单台机器上串行执行命令，并返回结果至字典"""
        result = list()
        # print('[+]',type(obj),obj)
        for c in self.cmds:
            r = obj.run_cmd(c)
            result.append([c, r])
            # try:
            #     r = obj.run_cmd(c)
            # except Exception as er:
            #     self.write_file(str(er))
            # else:
            #     result.append([c, r])
        return obj, result

    def concurrent_run(self):
        """并发执行"""
        future = ThreadPoolExecutor(self.max_worker)
        for obj in self.objs:
            try:
                future.submit(self.serial_exec, obj).add_done_callback(self.callback)
            except Exception as err:
                # err = self.color_str(err, "red")
                self.write_file(str(err))
        future.shutdown(wait=True)

    def callback(self, future_obj):
        """回调函数，处理返回结果"""
        ssh_obj, rlist = future_obj.result()
        # self.write_file(self.color_str("{} execute detail:".format(ssh_obj.h), "yellow"))
        #self.write_file("+" * 30)
        #self.write_file("{} execute detail:".format(ssh_obj.h))
        is_success = True
        for item in rlist:
            cmd, [code, res] = item
            if cmd == "df -P |sed -n '2, 1p'| awk '{print $5}' | cut -f 1 -d '%'":
                info = f"df_p | code => {code}|Result:{res}"
            else:
                info = f"mem_p | code => {code}|Result:{res}"
            # if code != 0:
            #     # info = self.color_str(info, "red")
            #     is_success = False
            #     if ssh_obj.h not in self.failed_hosts:
            #         self.failed_hosts.append(ssh_obj.h)
            # else:
            #     info = self.color_str(info, "green")
            self.write_file("{}execute detail:{}".format(ssh_obj.h,info))
            #self.write_file("-" * 30)
        if is_success:
            self.success_hosts.append(ssh_obj.h)
            if ssh_obj.h in self.failed_hosts:
                self.failed_hosts.remove(ssh_obj.h)

    def overview(self):
        """展示总的执行结果"""
        # for i in self.success_hosts:
        #     self.write_file("[-]",self.color_str(i, "green"))
        # for j in self.failed_hosts:
        #     self.write_file("[=]",self.color_str(j, "red"))
        info = "Success hosts {}; Failed hosts {}."
        s, f = len(self.success_hosts), len(self.failed_hosts)
        # info = self.color_str(info.format(s, f), "yellow")
        info = info.format(s, f)
        self.write_file(info)
        #self.write_file("+-" * 30)

    def write_file(self,message):
        # 将结果写入文件
        with open('1.txt','a+') as f:
            f.write(message+'\n')

    #装饰器;字体颜色
    # @staticmethod
    # def color_str(old, color=None):
    #     """给字符串添加颜色"""
    #     if color == "red":
    #         new = "\033[31;1m{}\033[0m".format(old)
    #     elif color == "yellow":
    #         new = "\033[33;1m{}\033[0m".format(old)
    #     elif color == "blue":
    #         new = "\033[34;1m{}\033[0m".format(old)
    #     elif color == "green":
    #         new = "\033[36;1m{}\033[0m".format(old)
    #     else:
    #         new = old
    #     return new

def dict_host_list(server_,cmd_=None):
    if isinstance(server_,dict):
        # 获取服务器字典，拆分关键字，组装并发服务器对象
        for key in server_:
            h = server_[key][0]
            p = server_[key][1]
            u = server_[key][2]
            w = server_[key][3]
            obj = SSHParamiko(h, p, u, w)
            obj_list.append(obj)
        return obj_list
    else:
        # 获取单服务器参数列表，拆分关键字，组织单连服务器对象
        h = server_[0]
        p = server_[1]
        u = server_[2]
        w = server_[3]
        obj = SSHParamiko(h, p, u, w)
        # obj.run_cmd(cmd_)
        return obj

import smtplib
from email.header import Header
from email.mime.text import MIMEText
#from config import gol 引入配置文件

class SendMail(object):
    def __init__(self):
        """ 初始化邮箱模块 """
        try:
            #self.mail_host = gol.get_value("mail_host")  # 邮箱服务器；引入配置项，获取值
            self.mail_host = "smtp.isoftstone.com"
            self.mail_port = 25  # 邮箱服务端端口
            self.mail_user = "xxxx@xxxx.com"  # 邮箱用户名
            self.mail_pwd =  "xxxx" # 邮箱授权码，163邮箱特有;其他邮箱不需启用SSL，直接使用密码
            self.mail_receivers = "xxx@qq.com".split(',')  # 收件人,以逗号分隔成列表
            smtp = smtplib.SMTP()
            smtp.connect(self.mail_host, self.mail_port)
            #启用SSL发信，端口默认是465，163邮箱授权码使用ssl通信
            #smtp = smtplib.SMTP_SSL(self.mail_host,465)
            smtp.login(self.mail_user, self.mail_pwd)
            self.smtp = smtp
        except:
            print('发邮件---->初始化失败!请检查用户名和密码是否正确!')

    def send_mails(self, content):
        """ 发送邮件,不带附件 """
        try:
            message = MIMEText(content, 'plain', 'utf-8')
            message['From'] = Header("DevinX", 'utf-8')
            message['To'] = Header("系统警告", 'utf-8')
            subject = '各系统巡检信息'
            message['Subject'] = Header(subject, 'utf-8')
            self.smtp.sendmail(self.mail_user, self.mail_receivers, message.as_string())
            print('发送邮件成功!')
        except Exception as e:
            print('发邮件---->失败!原因:', e)
    
    def send_mail_file(self,path_):
        self.path_ = path_
        print(self.path_)
        with open(self.path_,"r",encoding='utf-8') as f:
            content_ = f.read()
        print(content_)
        self.send_mails(content_)

    def mail_close(self):
        """ 关闭邮箱资源 """
        self.smtp.close()




if __name__ == '__main__':
    #设置主机列表
    host_pass_147 = "xxxx"
    
    server_147 = {
        0:[]
    }
    

    
    df_p = "df -P |sed -n '2, 1p'| awk '{print $5}' | cut -f 1 -d '%'"
    # 获取第七行第五列的磁盘占用率
    mem_p = "df |awk '{if(NR==2){print int($3*100/$2)}}'"
    # 获取内存使用率
    cmds = [df_p, mem_p]
    """
    cmd_ = ['curl -I -s https://lec.jinyun-logistics.com/app/portal/index.html | head -1 | cut -d " "  -f2']
    default_ip=$(ifconfig|head -n 2|tail -n 1|cut -d ":" -f 2|cut -d " " -f 1) //获取默认IP
    DUG=$(df -h|grep "/$"|awk '{print $5}'|awk -F% '{print $1}')   //根系统占用情况
    df |awk '{if(NR==4){print int($5)}}'
    mem_use = $(df |awk '{if(NR==2){print int($3*100/$2)}}')             // 内存使用情况
    """

    #定义对象：列表类型
    obj_list = []
    #获取服务器列表，从字段转换
    # obj_list = dict_host_list(server_147)
    # obj_list = dict_host_list(server_171)
    obj_list = dict_host_list(server_test)
    #程序入口，服务器列表和执行的命令列表；对象实例化
    all_obj = AllRun(obj_list, cmds)
    #调用并发执行
    all_obj.concurrent_run()
    #获取总体结果输出
    all_obj.overview()
    #将结果作为邮件发送
   # sendMail = SendMail()
    #拼接邮件内容无附件时使用
    #sendMail.send_mails(''.join(content_list))
    #有附件地址，文件不大时，直接读取内容发送邮件
    #本地地址
    #path_ = r'E:\\study\\try\\locahost\\监控脚本-centos7-zabbix-sh\\1.txt'
    #服务器地址
   # path_ = r'/opt/checkscript/1.txt'
   # sendMail.send_mail_file(path_)
   # sendMail.mail_close()   #关闭连接


