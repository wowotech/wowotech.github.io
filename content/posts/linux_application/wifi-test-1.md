---
title: "Debian下的WiFi实验（一）：通过无线网卡连接AP"
date: 2016-03-08T18:42:57+08:00
url: "/linux_application/wifi-test-1.html"
gid: "269"
emlog_type: "blog"
summary: "\r\n\t最近入手了一台T450，顺便在上面安装了Windows和Debian \r\n8。一般而言，在windows下的时候通过WiFi上网毫无压力，当然，做为linuxer，我其实也很少在T450上启动windows，那么问题来\r\n了，如何在Debian 8下使用WiFi呢？\r\n\r\n\r\n\t具体的场景是这样的，我们家的网络是通过ADSL进入internet，ADSL \r\nmodem的网线连接到了台式机，"
author: "linuxer"
category: "Linux应用技巧"
category_alias: "linux_application"
tags: ["wpa_supplicant"]
views: 18548
comment_count: 5
aliases:
  - "/linux_application/269.html"
  - "/269.html"
---

一、前言

最近入手了一台T450，顺便在上面安装了Windows和Debian 8。一般而言，在windows下的时候通过WiFi上网毫无压力，当然，做为linuxer，我其实也很少在T450上启动windows，那么问题来了，如何在Debian 8下使用WiFi呢？

具体的场景是这样的，我们家的网络是通过ADSL进入internet，ADSL modem的网线连接到了台式机，而台式机经常被夫人霸占，我的T450的以太网口毫无用武之地。买个hub吧又想省点钱，好在在某些外事活动中被赠送了一个随身WiFi的小东西，这样台式机就变成了一个AP。同时，夫人还丢下一句话：你不是搞IT的吗，这么能，用WiFi吧。

好吧，反正有线无线都一样，只要能上网就OK了。本文主要记录T450笔记本在Debian 8系统上如何通过WiFi上网的。

二、基本术语

由于WiFi有很多的术语，我们必须要先理解其相关的术语，否则通过man看帮助文档都不是很容易看懂的。需要说明的是本文的术语不是定义，仅仅是为了方便那些没有WiFi经验读者，用通俗的语言描述这些WiFi名词而已，精准的定义请参考IEEE802.11的标准。

1、SSID、ESSID和BSSID

我们首先看看BSS是什么意思。所谓BSS就是basic service set，一组STA连接到了一个AP上就形成了一个BSS，BSS内有若干的STA（AP中也有一个STA），这些STA已经取得了同步（大家在同一个物理频道上，用同样的节拍在工作）。BSSID是basic service set identifier的缩写，用来表示一个BSS，实际中一般用BSS中的AP的MAC地址做为BSSID。

若干个互联的BSS形成一个ESS(extended service set)，而ESSID（Extended Service Set IDentifier），通俗的讲就是用来标识无线网卡要接入的网络的。需要注意的是：这里没有说接入的AP，因为实际上一个wifi网络中可能有多个AP，这些AP可以形成一个个的BSS（Basic Service Set），多个BSS可以组成一个ESS（Extended Service Set），因此ESSID其实就是标识ESS的ID的。

SSID就是service set identifier的缩写，是一个统称。

2、WEP、WPA、WPA2和802.11i

无线局域网的基础协议是IEEE 802.11，这个协议定义了Wireless LAN中MAC层和PHY层的规格。在这个WiFi基础协议中，数据加密采用了WEP（Wired Equivalent Privacy）的算法。从它的名字也可以看出，其目的是为了获取和有线局域网一样的安全性。WEP使用了RC4这种stream cipher，加密key可以是64 bit或者128 bit（对于用户而言，使用40bit或者104bit的WEP key，因此WEP key和24 bit的initialization vector共同组成了RC4的key）。配合WEP，有两种鉴权方法：一种是Open System authentication（其实就是不鉴权，任何的STA都可以连接到AP，虽然可以连接到AP，但是无线传输的数据都是WEP加密的，因此，如果要让STA正常工作，它也需要有和AP一样的WEP key），另外一种是Shared Key authentication。Shared Key安全性好过Open System authentication（有总比没有强嘛），其基本过程分四步：

（1）STA发起鉴权请求

（2）AP收到鉴权请求后，下发一段明文（challenge-text）给STA

（3）STA用自己的WEP key对challenge text进行加密并回送AP

（4）AP用自己的WEP key解密，如果和自己之前下发的challenge text一样，那么就通过鉴权，允许该STA连接到AP。

由于WEP的安全性不好，WiFi联盟（Wi-Fi Alliance）开发了新的安全协议和安全认证的方法，也就是WPA（Wi-Fi Protected Access）以及WPA2，WPA2在2004年被批准成为IEEE802.11i。我们分成两个部分来看新协议对通信安全的增强。首先是加密方面，WEP容易被攻破，wifi联盟紧急提出了一个叫做TKIP (Temporal Key Integrity Protocol)的协议。这种方法沿用了WEP的RC4加密方法（可以兼容旧的硬件，毕竟厂商们已经卖了辣么多的WiFi设备），密钥的长度是128 bit。不过TKIP对key进行了改进，不再是固定的一个key，而是为每一个发送的package使用不同的key，从而增强了破解的难度。为了进一步增强安全性，在WPA2（802.11i）中，一种叫做CCMP (CTR mode with CBC-MAC Protocol)的协议被制定出来。这个协议是基于AES的，反正是安全性很好，具体如何好如果有兴趣请自行网上查阅。其次，我们再来看看鉴权方面。STA接入网络而获取服务是需要认证的，在STA上发起认证请求的实体就是supplicant，而接收请求的就是Authenticator，对于WiFi而已，一般Authenticator实现在AP侧，负责处理来自各个连接到AP的认证请求。还有一个实体叫做Authentication Server，该实体是真正校验来自supplicant的证书，判断持有该证书的STA是否允许接入网络，并将结果反馈给AP中的Authenticator实体。在鉴权过程的初期阶段（生成Pairwise Master Key，即PMK），WPA2支持两种方法：

（1）PSK（pre-shared key）。PSK是一个密码学上的术语，其实就是交互信息的双方预先都知道的一个密钥（PSK），这个密钥是通过其他安全途径进行共享，和wifi这个通信途径无关。

（2）EAP（Extensible Authentication Protocol）。TODO

基本上，在个人环境或者微小企业环境下，PSK的方法（WPA-Personal）就OK了，因此，本文进行wifi实验的时候就选择了PSK的方法。PSK有写陌生，其实大家熟悉的都是所谓接入网络的密码（password），其实也就是大家输入对话框的一个ASCII字符串，这是用户可见的。但是，实际上进行通信的时候需要的是256 bit的key（PSK），只要双方持有的这个256bit的key是相同的，那么就OK啦。不过使用PSK比较麻烦，因此为了用户方便实际上双方共享的PSK都是通过passphrase或者password加上SSID计算出来的，因此，实际上用户配置wpa的passphrase就可以了，内部会有算法将passphrase转换成PSK（Note：我们可以用wpa\_passphrase这个工具来生成256 bit的key）。

具体各种复杂的安全相关的内容这里就不介绍了（不要问为什么，因为我也没有搞懂，希望后续有机会能研究以下），大家自行补脑吧。

三、软件准备

通过WiFi上网主要是通过一个叫做wpa supplicant的软件，本章描述了两种方面获取该软件。第一种是通过Debian自己的包管理工作来安装WiFi软件，另外一种是自己动手，丰衣足食。

1、利用apt-get来获取wpa supplicant软件。命令如下：

> sudo apt-get install wpasupplicant

安装了该wifi软件包之后，其实就是在系统中增加了下面相关的文件，罗列如下：

|  |  |
| --- | --- |
| 文件名 | 描述 |
| /var/cache/apt/archives/wpasupplicant\*.deb | wpasupplicant的安装包文件 |
| /var/lib/dpkg/info/wpasupplicant.\* | 这里保存了关于wpasupplicant安装包的一些信息。例如该安装包的MD5文件、该安装包的安装文件列表等等。 |
| /usr/share/man/man5/wap\_supplicant.conf.5.gz | 关于如何配置wpa\_supplicant的manual信息。    用户可以通过man wpa\_supplicant.conf看到这些信息 |
| /usr/share/man/man8/wap\_supplicant.8.gz | 关于wpa\_supplicant的概述、功能、命令行参数等manual信息。    用户可以通过man wpa\_supplicant看到这些信息 |
| /usr/share/man/man8/wap\_action.8.gz | 关于wpa\_action的概述、功能、命令行参数等manual信息。    用户可以通过man wpa\_action看到这些信息 |
| /usr/share/man/man8/wap\_background.8.gz | 关于wpa背景知识的描述。    用户可以通过man wpa\_background看到这些信息 |
| /usr/share/man/man8/wap\_cli.8.gz | 关于wpa\_cli的概述、功能、命令行参数等manual信息。    用户可以通过man wpa\_cli看到这些信息 |
| /usr/share/man/man8/wap\_passphrase.8.gz | 关于wpa\_passphrase的概述、功能、命令行参数等manual信息。    用户可以通过man wpa\_passphrase看到这些信息 |
| /usr/share/doc/wpasupplicant/\* | 各种各样的文档，可以看看，很有意思的 |
| /usr/share/dbus-1/system-serive/    fi.w1.wpa\_supplicant1.service | wpa supplicant服务其实不需要启动后就立刻激活（通过init system），可以考虑通过dbus接口由用户激活该服务。既然需要dbus来启动启动service，那么就需要定义该service的一些属性，例如启动命令和传入的参数什么的，这些信息定义在dbus service file中，而这个文件就是wpa supplicant的dbus service file |
| /sbin/wpa\_supplicant | wpa supplicant的主程序 |
| /sbin/wpa\_cli | wpa supplicant的客户端程序，可以通过control interface和wpa supplicant daemon进程进行通信，控制其执行。 |
| /sbin/wpa\_action | 这是一个被wpa\_cli使用的脚本，wpa\_cli可以从wpa supplicant daemon中获取无线网卡的状态信息事件（connect event或者disconnect event），然后会调用wpa\_action进行相应的处理。 |
| /usr/bin/wpa\_passphrase | 该工具用来将用户使用的ASCII码的password（passphrase）以及SSID转换成WPA的256 bit的PSK。 |
| /etc/network/if-pre-up.d/wpasupplicant    /etc/network/if-up.d/wpasupplicant    /etc/network/if-down.d/wpasupplicant    /etc/network/if-post-down.d/wpasupplicant | 这些文件都是符号连接，都是指向了/etc/wpa\_supplicant/ifupdown.sh文件。 |
| /etc/ifplugd/action.d/action\_wpa | 该文件也是符号连接，指向了/etc/wpa\_supplicant/action\_wpa.sh文件    这个文件是配合ifplugd daemon而支持网卡设备的hotplug。 |
| /etc/wpa\_supplicant/ifupdown.sh    /etc/wpa\_supplicant/functions.sh | 这些脚本是配合ifupdown framework的。具体可以参考ifup或者ifdown命令的manual。 |
| /etc/wpa\_supplicant/action\_wpa.sh | 这个文件是配合ifplugd daemon而支持网卡设备的hotplug。 |
| /lib/systemd/system/wpa\_supplicant.service | wpa\_supplicant服务如果需要systemd启动，那么需要一个service类型的unit配置文件（systemd需要），wpa\_supplicant.service用来告知systemd如何来启动wpa\_supplicant服务。 |
| /etc/dbus-1/system.d/wpa\_supplicant.conf | message bus daemon是通过配置文件来约定其行为以便适应不同的应用场景。例如systemwide message bus就是一种适合传递设备信息（例如无线网卡up/down的信息）的message bus，因此，wpa\_supplicant实际上需要连接到systemwide message bus，而该bus的主配置文件是/etc/dbus-1/system.conf，也包括/etc/dbus-1/system.d目录下的各个配置文件。wpa\_supplicant.conf就是for wpa supplicant应用的那个配置文件。 |
| /etc/wpa\_supplicant/wpa\_supplicant.conf | wpa\_supplicant主程序运行会需要一个配置文件，wpa\_supplicant.conf就是这个配置文件 |

2、手动编译wpa supplicant

要想自己编译wpa supplicant，当然需要source code，可以通过下面的命令获取：

> git clone git://w1.fi/srv/git/hostap.git

当然，这个git仓库中不仅仅有wpa supplicant，还有hostap程序，不过这个程序和本文无关，略过。wpa supplicant是依赖libnl（netlink lib）和libssl（open ssl lib）这两个库的，因此我们首先要安装libnl和libssl的开发包：

> sudo apt-get install libnl-3-dev
>
> sudo apt-get install libssl-dev

安装完毕libnl和libssl的库文件以及必要的头文件之后，下面我们准备为wpa supplicant选择feature（wpa supplicant功能太多，你只需要选择你需要的功能）。配置文件是hostap/wpa\_supplicant/目录下的.config文件，我们可以从缺省的配置文件开始，命令如下：

> cp defconfig .config

defconfig是wap supplicant源代码自己带的配置文件，我们以它为起点，对.config文件进行编辑。当然，其配置项目很多，我们简单描述其中几个：

> CONFIG\_DRIVER\_NL80211=y －－－－－－－－－－－－－－（1）
>
> CONFIG\_CTRL\_IFACE=y－－－－－－－－－－－－－－－－－（2）
>
> CONFIG\_WPS=y
>
> CONFIG\_P2P=y－－－－－－－－－－－－－－－－－－－－－（3）
>
> CONFIG\_AP=y

（1）wap supplicant是用户空间的程序，那么它是通过什么样子的接口和内核态的wifi网卡驱动进行通信呢？早期的接口叫做Linux wireless extension（对应CONFIG\_DRIVER\_WEXT），是一种ioctl type的接口。当netlink这种简单又好用的接口出现的时候，nl80211这样新的接口定义也随之而来。这个选项是用来配置wpa supplicant是否支持nl80211类型的driver。还有若干CONFIG\_DRIVER\_\*的配置项，大家自行阅读注释就OK了。

（2）wap supplicant是一个daemon，可以提供各种服务，而wpa cli是一个客户端程序，可以通过命令行的方式来和wpa supplicant daemon进行交互，交互的管道是什么呢？CONFIG\_CTRL\_IFACE就是用来配置这个通信用的管道，具体的术语叫做control interface。

（3）是否支持WiFi直连（Wi-Fi Direct）。这是一个很有意思的功能，后续可以另起一篇文章专门描述之。

大概的概念就是类似，大家可以自己试着进行配置。选择了feature list之后，还需要修改一些库和头文件的路径，其实主要就是配置libnl和libssl的路径，如下：

> CFLAGS += -I/usr/include/libnl3－－－－－－－－－－－－for libnl
>
> LIBS += -L/lib/x86-64-linux-gnueabihf
>
> CONFIG\_LIBNL32=y－－－－－－－配置libnl的版本
>
> CFLAGS += -I/usr/include/openssl－－－－－－－－－－for libssl
>
> LIBS += -L/lib/x86-64-linux-gnueabihf

具体的路径大家可以根据实际情况修改。最后，来一个make就可以编译啦。

四、连接AP

1、关于wpa\_supplicant程序。

wpa\_supplicant其实就是实现了WPA的客户端操作以及IEEE802.1X supplicant端（即提出鉴权请求的那一端）的操作。该命令相关的命令行参数如下：

|  |  |
| --- | --- |
| 命令行参数 | 描述 |
| -D driver | wpa\_supplicant应用程序使用哪一种接口和wifi driver进行沟通？对于比较新的linux内核，nl80211是必然的选择。 |
| -B | 在后台运行wpa\_supplicant |
| -C | 指明control interface参数 |
| -c | 设定配置文件 |
| -d -dd | 加大打印日志的力度，-dd会进一步增加日志信息。主要用于调试 |
| -f | 将打印信息log到指定的文件中，缺省log会输出到stdout |
| -g | 配置全局的control interface的路径。如果使用了-g参数，那么各个interface的-C参数就无效了。 |
| -i | 指明wpa supplicant监听的无线网卡的名字，一般是wlanx（x是一个数字，例如wlan0）。可以指明多个interface name，不过要用-N分隔 |
| -K | 在debug信息中输出敏感的password信息 |
| -P | 指明保存该daemon的pid的文件 |
| -p | driver参数，优先级高于配置文件 |
| -s | 通过syslog输出日志。缺省是输出到stdout |
| -q -qq | 和-d -dd是相反的操作 |
| -T | 通过Linux tracing系统输出日志。缺省是输出到stdout |
| -t | debug信息中增加timestamp |
| -u | 使能DBus control interface |

2、配置文件

除了命令行参数可以控制wpa\_supplicant的运行，配置文件也能影响其行为，具体如下：

|  |  |
| --- | --- |
| 配置项 | 描述 |
| update\_config | 是否允许wpa\_supplicant程序修改配置文件。 |
| ctrl\_interface | 对于linux或者unix而言，可以采用domain socket做为控制接口。/var/run/wpa\_supplicant是一个推荐的配置。 |
| ap\_scan | 配置scan AP的行为。    如果等于1，说明由wpa supplicant来启动AP scan过程，scan之后会在其中选择一个合适的进行连接。如果没有合适的AP，也可以根据配置setup IBSS或者进入AP mode    如果等于0，那么wpa supplicant将不启动任何的scan ap并进行连接的行为，一切都交给driver自己搞定吧。    如果driver接口使用nl80211的时候（大部分的linux的场景），该参数不能等于2。 |
| passive\_scan | 是否使能passive scan |
| driver\_param | 配置driver的参数 |
| country | 配置国家码 |
| device\_name    manufacturer    model\_name    serial\_number    device\_type | WiFi设备的信息 |
| bss\_max\_count | 这是wpa supplicant能够保存scan结果的上限，缺省是200，也就是说最多保存200个scan result entry。 |
| ext\_password\_backend | 有可能password保存在某些外设上，这里是对这些保存password的后端进行配置。 |
| 下面的配置项是属于一个network block的 |  |
| disabled | 该network block是否是enable的。如果想用于P2P GO，那么disable应该等于2。 |
| id\_str | Network ID字符串 |
| SSID | 无线局域网的名字 |
| scan\_ssid | 配置scan的方式 |
| bssid | 如果配置了该参数，那么说明只和该bssid对应的那个AP进行连接 |
| mode | 0：工作在STA模式（即Managed mode），和AP连接    1：IBSS mode    2：AP mode |
| key\_mgmt | 能接受的鉴权密钥管理协议，可能的配置包括：    WPA-PSK    WPA-EAP    …… |
| psk | 配置password |
|  |  |

上表只罗列出部分的配置项，其他的可以参考wpa\_supplicant目录下wpa\_supplicant.conf文件中的注释。

3、实际动手

首先编辑一个/etc/wpa\_supplicant/home.conf文件，内容如下：

> network={
>
> ssid="your AP SSID"
>
> key\_mgmt=WPA-PSK
>
> psk="your AP password"
>
> }

为了不暴露我们家wifi的信息，这里隐去了部分关键信息，^\_^。

启动wpa supplicant程序，命令如下：

> Sudo wpa\_suplicant –B –iwlan0 –Dnl80211 –c/etc/wpa\_supplicant/home.conf

完成该命令后，可以iw dev wlan0 link查看连接信息，通过打印可以看出来，T450的无线网卡wlan0已经连接到了我们家的随身WiFi的AP上了，不过还没有IP地址，这也简单，动态分配一个，命令如下：

> sudo dhclient wlan0

通过ifconfig可以看到wlan0已经有了IP地址，至此，T450可以愉快的上网了。

*原创翻译文章，转发请注明出处。蜗窝科技*
