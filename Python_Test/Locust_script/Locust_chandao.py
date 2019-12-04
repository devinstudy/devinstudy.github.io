'''
Locust压力测试工具
	python3 库的集成
		http/https协议		 ==> Requests		协议支持的一种
		协程（微线程）		 ==> gevent			高并发
		web开发框架			 ==> flask 			类似django
		二进制序列化格式	 ==> msgpack-python	类似json数据
		2与3差异封装工具	 ==> six			提供工具的库
		分布式				 ==> pyzmq			实现分布式的库
	Locust原始部署
		python -V ==> install python3
			wget https://www.python.org/ftp/python/3.6.3/Python-3.6.3.tgz
			tar zxvf Python-3.6.3.tgz
			cd Python-3.6.3
			./configure --prefix=/home/locust/python3
			make && make install
			mv /usr/bin/python /usr/bin/python.bak
			ln -s /home/locust/python3/bin/python3.6 /usr/bin/python
			#vim /usr/libexec/urlgrabber-ext-down
			vim /usr/bin/yum
				#! /usr/bin/python ===> #! /usr/bin/python2
		pip -V ==> add pip  path
			#wget https://bootstrap.pypa.io/get-pip.py
			#python get-pip.py
			ln -s /home/locust/python3/bin/pip /usr/bin/pip
		pip install Locust
			locust -V
				ln -s /home/locust/python3/bin/locust /usr/bin/locust

	第一个demo：User蝗虫+Task指令（使用参数登录，然后以2:1概率访问/页和about页）
		from locust import HttpLocust，TaskSet，task
			class
				method :	WebsiteTasks <=== TaskSet <=== locust
				user:		WebsiteUser <=== HttpLocust <=== locust
		class WebsiteTasks(TaskSet):
		def on_start(self):
			self.client.post("/login",{"username":"test","password":"123456"})

		@task(2)
		def index(self):
			self.client.get("/")

		@task(1)
		def about(self):
			self.client.get("/about/")

		class WebsiteUser(HttpLocust):
			task_set = WebsiteTasks
			host = "http://debugtalk.com"
			min_wait = 1000
			max_wait = 5000

		locust -f xxxx.py --host='http://xxxxx' --web-host="127.0.0.1"

	二次开发
		class HttpLocust(Locust)
			client属性：对应着虚拟用户作为客户端所具备的请求能力
			task_set属性：指向一个TaskSet类，TaskSet类定义了用户的任务信息，该属性为必填
			host属性：被测系统的host，当在终端中启动locust时没有指定--host参数时才会用到
			weight属性：同时运行多个Locust类时会用到，用于控制不同类型任务的执行权重
			max_wait/min_wait属性：每个用户执行两个任务间隔时间的上下限（毫秒），具体数值在上下限中随机取值，若不指定则默认间隔时间固定为1秒
		class TaskSet：实现了虚拟用户所执行任务的调度算法
			定义任务信息：
				schedule_task：规划任务执行顺序
				execute_next_task：挑选下一个任务
				execute_task：执行任务
				wait：休眠等待
				interrupt：中断控制
			初始化任务：
				on_start函数：正式测试前执行一次（类似LR中的vuser_init）
					HttpLocust使用到了requests.Session，后续任务都能具有登录态
		方向1：其他协议系统
			对于HTTP(S)以外的协议，需要自行实现客户端
			通过注册事件的方式
				请求成功时触发events.request_success，
				请求失败时触发events.request_failure。
			创建一个继承自Locust类的类，对其设置一个client属性并与实现的客户端绑定。
			和使用HttpLocust类一样，测试其它协议类型的系统
		方向2：关联
			例如构造请求时先从之前的请求的Responese中提取所需参数session-id等
			LR：录制自动关联，效果不好
				手动调整==>注册型函数web_reg_save_param
							根据左右边界或其它特征定位到参数值并将其保存到参数变量
			LT：脚本实现==>python的re.search
					针对html页面，还可以使用lxml库：etree.HTML(html).xpath实现元素定位
		方向3：参数化
			循环取数据，数据可重复使用：
				模拟3用户并发请求网页，总共有100个URL地址，每个虚拟用户都会依次循环加载这100个URL地址；
			保证并发测试数据唯一性，不循环取数据：
				模拟3用户并发注册账号，总共有90个账号，要求注册账号不重复，注册完毕后结束测试；
			保证并发测试数据唯一性，循环取数据
				模拟3用户并发登录账号，总共有90个账号，要求并发登录账号不相同，但数据可循环使用。
			LR：集成的参数化模块，直接配置参数化策略
			LT：python的list和queue数据结构
				在WebsiteUser定义一个数据集，所有用户在WebsiteTasks中共享数据集
					不要求数据唯一性：数据集选择list数据结构，遍历
					要求唯一性，不循环：数据集选择queue数据结构，queue.get()操作
					要求唯一性，循环：queue.get()操作，取完插入到队尾queue.put_nowait(data)
		方向4：检查点
			LR：web_reg_find注册函数进行
			LT：对响应内容关键字进行断言assert xxx in response
		方向5：集合点
			LT：未做封装，可自行封装，例如
				from locust import events
				from gevent._semaphore import Semaphore
				all_locusts_spawned = Semaphore()
				all_locusts_spawned.acquire()

				def on_hatch_complete(**kwargs):
					all_locusts_spawned.release()

				events.hatch_complete += on_hatch_complete

				class TestTask(TaskSet):
					def on_start(self):
						""" on_start is called when a Locust start before any task is scheduled """
						self.login()
						all_locusts_spawned.wait()
		方向6：分布式

'''
from locust import HttpLocust,TaskSet,task,between
from requests.exceptions import (RequestException, MissingSchema,InvalidSchema, InvalidURL)
import queue,json


class WebsiteTasks(TaskSet):

	# locust重写响应判定标准后，需要重写locust失败判定，否则locust无法判断
	def check_response(self, response):
		try:
			response.raise_for_status()
		except RequestException as e:
			events.request_failure.fire(
				request_type=response.locust_request_meta["method"],
				name=response.locust_request_meta["name"],
				response_time=response.locust_request_meta["response_time"],
				exception=e,
			)
		else:
			# 重写响应判定标准
			code = response.json().get("code")
			if code == 0:
				events.request_success.fire(
					request_type=response.locust_request_meta["method"],
					name=response.locust_request_meta["name"],
					response_time=response.locust_request_meta["response_time"],
					response_length=response.locust_request_meta["content_size"],
				)
			else:
				events.request_failure.fire(
					request_type=response.locust_request_meta["method"],
					name=response.locust_request_meta["name"],
					response_time=response.locust_request_meta["response_time"],
					response_length=response.locust_request_meta["content_size"],
					exception="Response Code Error! Code:{0}".format(code)
				)

	def login_one(self):
		'''单账号登录'''
		login_url = '/user-login.html/'
		head_ = {
			"User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36",
			"Content-Type": "application/x-www-form-urlencoded",
		}
		body_ = {
			"account":'test_8888',
			"password":'12345678'
			}
		r = self.client.post(login_url,data=body_,catch_response = True,headers=head_)
		# print(r.text)
		assert "parent.location='/zentao/index.html'" in r.text

	def on_start(self):
		'''初始化工作，只执行一次'''
		self.login_one()

	# 访问我的地盘
	@task(2)
	def my_(self):
		r = self.client.get("/my/")
		# print(r.text)
		assert "我的地盘" in r.text
		# 	self.check_response(re_my_)
		# except Exception as err:
		# 	raise Exception("request getChatMessage fail:{0}".format(err))

	#访问BUG页面
	@task(1)
	def bug_(self):
		r = self.client.get("/project-bug-11.html")
		assert "提Bug" in r.text

	# 退出登录
	def login_out(self):
		r = self.client.get("/zentao/user-logout.html")
		# print(r.text)
		assert "self.location='/zentao/user-deny-zentao/user-logout.html'" in r.text

	# 程序退出/清理
	def on_stop(self):
		'''退出，清理工作,只执行一次'''
		self.login_out()

	#批量账号登录
	# @task(1)
	# def login_(self):
	# 	try:
	# 		login_name =  self.locust.idqueue.get() # 获取队列里的数据
	# 	except Exception as er:
	# 		print("no data exist")
	# 		exit(0) # 队列取空后，直接退出
	# 	else:
	# 		body_ = {
	# 			"username":login_name,
	# 			"password":"12345678"
	# 			}
	# 	try:
	# 		re_login = self.client.post("/user-login.html",body_,catch_response = True)
	# 		self.check_response(re_login)
	# 	except Exception as err:
	# 		raise Exception("request getChatMessage fail:{0}".format(err))

class WebsiteUser(HttpLocust):
	task_set = WebsiteTasks
	host = "http://10.242.129.90:8082/zentao/"
	# min_wait = 1000
	# max_wait = 5000
	# min_wait和max_wait在0.13版本被禁用，替代的是wait_time =  between(1, 5),between需要import库
	wait_time = between(3,5)
	# weight = 2
	# 默认weight的权重为10
	# 生成测试数据
	# iddate = ['test_'+str(i) for i in range(8887,8889)]
	# # 添加到队列
	# idqueue = queue.Queue()
	# for i in iddate:
	# 	idqueue.put_nowait(i)
