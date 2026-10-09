---
title: "Debian下的WiFi实验（二）：无线网卡自动连接AP"
date: 2016-03-24T18:18:57+08:00
url: "/linux_application/wifi-test-2.html"
gid: "274"
emlog_type: "blog"
summary: "自从我的T450能够WiFi上网之后，在Debian下上网，更新软件包什么的再也不用看老婆的脸色了，哈哈。虽然如此，但是隐隐约约总是觉得很 不方便，对了，就是每次开机都需要输入一系列的命令，之后才能愉快的玩耍，唉！如果无线网卡能自动连接AP并且自动分配IP地址就好了。人类就是这么懒惰 （当然也可以说是为了提高用户体验），而懒惰也不断的推进技术的进步。 本文主要描述Debian 8下面，如何配置无线"
author: "linuxer"
category: "Linux应用技巧"
category_alias: "linux_application"
tags: ["systemd", "wifi", "udev"]
views: 17561
comment_count: 1
aliases:
  - "/linux_application/274.html"
  - "/274.html"
---

一、前言

自从我的T450能够WiFi上网之后，在Debian下上网，更新软件包什么的再也不用看老婆的脸色了，哈哈。虽然如此，但是隐隐约约总是觉得很不方便，对了，就是每次开机都需要输入一系列的命令，之后才能愉快的玩耍，唉！如果无线网卡能自动连接AP并且自动分配IP地址就好了。人类就是这么懒惰（当然也可以说是为了提高用户体验），而懒惰也不断的推进技术的进步。

本文主要描述Debian 8下面，如何配置无线网卡在开机过程中自动连接AP。如果你非常着急，可以直接去看第五章，那里说明了如何修改配置完成这一目标。如果你想了解这个开机过程wifi如何自动连接AP的过程，中间的三个章节给出了一些细节说明。

二、systemd在启动过程中需要启动那些service？

在传统的SysV init场景下，一切都很简单，在某个runlevel的目录下（对于runlevel 3而言，目录是/etc/rc3.d）有很多很多的脚本（符号链接到/etc/init.d目录下的某个脚本），K打头的脚本就是进入该runlevel需要stop的service，而S打头的脚本就是进入该runlevel需要start的service。解决service之间的依赖关系也很简单，用S或者K之后的两个数字来控制执行顺序。多么美妙的生活啊，不过都被Lennart Poettering给搅乱了，听说有激进者对其进行人身攻击甚至是死亡威胁，我一点都不奇怪。当然，我对systemd没有意见，甚至是隐约赞同其做法（实际上，在我们自己的产品中，我们甚至使用了和systemd类似的方法，即干掉脚本，用c代码完成启动过程）。孰是孰非这里就不讨论了，但是潮流似乎是不可逆转了，我们必须要面对systemd，谁叫我安装的是Debian 8呢，呵呵～～～。

1、systemd如何自动启动服务？

systemd的核心概念就是unit，当内核把控制权交给systemd之后，系统进入systemd全面把控的状态。简单的说呢其实就是处理一个一个的unit。为了好控制，systemd的启动过程被分成了若干个叫做target的unit（具有相同特性的unit分组成为一个个的target）。“grouping”或者说“分组”是一个值得思考的术语：如果你能真正了解每一个个体的特性，那么你就有能力对其进行分组，如果你能正确的对杂乱无章的个体进行分组，那么你已经是站在一个更高的层次上来观察个体行为了。算了，扯远了，结论就是：systemd启动过程实际上是被分成了若干个target unit了。虽然如此，这里并不是说各个target unit阶段是是有时间顺序安排的，各个target unit仍然是并发处理的。

就像内核去找init一样，init只是一个代号，表示PID等于1的那个进程，可能是systemd，也可能是systemX什么的，anyway，kernel就知道一点：它要启动的是init。实际上，对于使用systemd的系统，其也存在init，只不过是一个符号链接：

> lrwxrwxrwx 1 root root 20 Nov 21 14:00 /sbin/init -> /lib/systemd/systemd

同样的道理，systemd也需要一个“符号”，它表示systemd启动的第一个target，它就是default.target，我们来看看我计算机上的default.target，如下：

> lrwxrwxrwx 1 root root 37 Mar 10 11:16 /etc/systemd/system/default.target -> /lib/systemd/system/multi-user.target

一般而言，default.target也是一个符号链接，一般会链接到graphical.target（原来的runlevel 5）或者multi-user.target（原来的runlevel 3）。对于一个痴迷与字符界面的工程师，当然是multi-user.target了。

确定了第一个要处理的default.target之后，还需要回答一个问题：systmed到哪里去找它呢？实际上，不只是寻找target，systemd按照同样的规则寻找unit。对于system mode的systemd，搜索的目录顺序如下：

（1）/etc/systemd/system （本地配置目录）

（2）/run/systemd/system （runtime unit）

（3）/lib/systemd/system （unit file的安装目录）

OK，有了目录以及文件名，我们可以精准的目中一个default.target，如下：

> [Unit]   
> Description=Multi-User System   
> Documentation=man:systemd.special(7)   
> Requires=basic.target   
> Conflicts=rescue.service rescue.target   
> After=basic.target rescue.service rescue.target   
> AllowIsolate=yes

该文件的语法符合XDG Desktop Entry Specification，如果熟悉windows上.ini文件的话，你同样也会感到眼熟。通用的关于unit file的内容都是定义在[Unit]和[Install]小节中。这里面Requires这个配置项是关于依赖性的配置，也就是说如果default.target被激活（systemd缺省执行该target，那么default.target当然是activated），那么Requires所配置的那一串unit file也必须被激活。所谓激活，其实就是执行该unit。对应这个场景，basic.target也必须在启动过程中被启动起来。其内容如下：

> [Unit]   
> Description=Basic System   
> Documentation=man:systemd.special(7)   
> Requires=sysinit.target   
> Wants=sockets.target timers.target paths.target slices.target   
> After=sysinit.target sockets.target timers.target paths.target slices.target

Wants其实Requires是类似的，只不过Wants是一个弱化版本的Requires（有兴趣的话读者可以自行阅读Wants和Requires有何不同），同样的，如果basic.target需要被激活，那么Wants列表中的sockets.target timers.target paths.target slices.target这些target都需要被启动起来。现在，我们已经了解到了，一个default.target，拎起来那么多的target，如果我们继续下去，可以看到更多的unit被拎起来。除了Wants和Requires之外，还有一个更强劲的工具，就是xxx.wants目录。比如对于multi-user.target而言，可能存在multi-user.target.wants目录，如果存在的话，那么该目录下的所有的unit file都会自动添加到multi-user.target中的Wants配置项的后面，而不需要手动的修改multi-user.target这个unit file。对于我的T450而言，其目录下的unit file包括：

> cron.service   
> pppd-dns.service   
> remote-fs.target   
> rsyslog.service   
> ssh.service

最后需要强调的是：本小节的Requires和Wants所定义的依赖关系仅仅是相互连带关系，即一个unit需要启动起来，那么其Requires（或者Wants）列出的所有的unit也必须要启动起来。而一个unit需要被stop，那么其连带的所有unit都需要被停止。这些关系中并不存在启动顺序的限制，A unit Requires（或者Wants）B unit，并不意味着A unit完成之后再启动B unit，systemd会把它们最大可能性的并发执行。

2、如何控制启动顺序？

虽然通过一些技巧（例如在[why systemd](/linux_application/why-systemd.html)中描述的解除socket依赖关系的方法）可以解除各种unit之间的依赖关系，不过有些时候，各种unit file之间的启动顺序的依赖关系无法跨越。我们一起来看看[serial-getty@.service](mailto:serial-getty@.service)：

> [Unit]   
> Description=Serial Getty on %I   
> Documentation=man:agetty(8) man:systemd-getty-generator(8)   
> Documentation=<http://0pointer.de/blog/projects/serial-console.html>  
> BindsTo=dev-%i.device   
> After=dev-%i.device systemd-user-sessions.service plymouth-quit-wait.service
>
> ……

从名字上应该可以推测出来这个service unit file应该是和串口登录有关，文件名中的@充满了神秘的色彩，到底是干什么的？我们可以考虑这样的一个场景，系统中有三个串口，如果需要在3个串口上提供getty的服务，那么需要三个unit file。但是其实这三个串口登录服务的unit file非常的类似，虽然说重要的事情重复三遍比较好，但是程序员都是懒惰的，于是systemd提供一种模板服务，也就是说一个unit file可以通过一个模板unit来创建。创建过程是怎样的呢？原来systemd在通过unit file name寻找该unit的时候，首先当然是全字匹配了，如果不成功，systemd就会看看文件名中是否有@，如果有，那么就去掉@之后的字符（当然不会去掉.target或者.service这样包括unit type的字符了），然后继续进行匹配。因此，对于[serial-getty@ttyS0.service](mailto:serial-getty@ttyS0.service)而言（在系统的第一个串口上登录），如果系统没有全字匹配的unit file，那么systemd会退而求其次去寻找[serial-getty@.service](mailto:serial-getty@.service)这个模板，如果找到，那么也OK，只不过ttyS0这个字符串会传递给模板。而在模板中％i其实就是ttyS0这个具体实例化时候的字符串。因此，[serial-getty@.service](mailto:serial-getty@.service)这个模板中的BindsTo=dev-%i.device在本场景中实际上表示BindsTo=dev-ttyS0.device.

这里还需要顺便描述一下BindsTo这个配置项，这个配置项和Require类似，不过附加多一条功能就是：当dev-ttyS0.device这个unit突然消失的时候，那么本service，即[serial-getty@ttyS0.service](mailto:serial-getty@ttyS0.service)也必须停掉。谁能这么自由，来去如风，不受systemd的控制呢？相信你已经猜到了，是device，设备可以随时插入或者拔出，此外mount point也会突然消失，因此用户会umount某一个挂载点而不事先通知systemd。

After这个配置项是用来控制顺序的。对应我们这个场景，After=dev-%i.device systemd-user-sessions.service plymouth-quit-wait.service表示本unit必须在这三个unit file之后启动，这也就严格约束了unit之间的先后顺序。Before配置项和After类似，只不过是相反的操作，这里就不再描述了，不过需要注意的是：Before和After都是控制顺序，并不表示unit之间的连带关系（那是Requires、Wants等配置项的功能）。

三、systemd如何加载驱动模块？

1、静态加载的方式

systemd提供了一个叫做systemd-modules-load.service的服务，该服务可以用来在系统启动过程中从一个静态的配置文件中加载若干的linux 模块。该服务的unit file如下：

> [Unit]   
> Description=Load Kernel Modules   
> ……
>
> [Service]   
> Type=oneshot   
> RemainAfterExit=yes   
> ExecStart=/lib/systemd/systemd-modules-load

在这里，我们可以简单介绍一下Service小节的配置项。Type配置项定义了systemd如何启动该service，主要的类型包括：simple, forking, oneshot, dbus, notify和idle。如果Type是simple的话，那么ExecStart配置项定义的就是该service的主进程。在这种模式下，如果该service向系统中的其他进程提供了某些服务，那么其他进程和该service进程之间的通信管道必须先建立好（例如让systemd建立socket）。而systemd在处理完该service之后，不会停留，会立刻去启动其他的service。oneshot和simple类似，不过systemd不会立刻启动其他的service，直到该service退出执行。其他类型的service我们后续遇到适合的场景再描述吧。

静态配置文件的名字是xxx.conf的文件，在启动过程中，systemd-modules-load.service会从下面的路径中加载内核模块：

> `/etc/modules-load.d/*.conf`
>
> `/run/modules-load.d/*.conf`
>
> `/usr/lib/modules-load.d/*.conf`

2、动态加载的方式

动态加载的方式本质上就是一种从内核捕获设备相关的信息，然后根据这些来自内核的device event来完成相应的动作，例如加载该设备的驱动，加载该设备需要的firmware，在/dev目录下建立一个对应的device node等等。在过去，有一个叫做udevd的daemon进程负责通过netlink socket接收这些设备消息（如果你足够老，你应该知道HAL这个东东，udev daemon代替了HAL daemon），然后按照一定的规则来处理消息。现在，udev的代码已经整合进入systemd（不要奇怪，systemd吞并了太多的软件模块的功能，这也是大家诟病其的原因之一）。

我们首先从service的角度看看系统是如何运作的。提供udev服务（包括动态加载模块服务）的是systemd-udevd.service。第一个问题：该服务会在启动过程中加载吗？当然会，如果你使用ps -ef命令可以看到一个systemd-udevd的service进程，问题是：该服务是如何被激活（Active）的呢？我的系统的default.target是指向了multi-user.target，而multi-user.target需要（Requires=basic.target）basic.target，而basic.target Requires sysinit.target这个unit。在/lib/systemd/system/sysinit.target.wants目录下有一个systemd-udevd.service的链接脚本文件。因此，通过一连串的依赖关系，systemd最终会启动systemd-udevd.service服务（后文简称udev）。

我们前面已经说过，udev是按照规矩办事情，也就是说匹配了一定的规则就执行相关的动作。这些匹配规则和动作组成了udev的Rules file。rules file的位置包括：

（1）/lib/udev/rules.d

（2）/run/udev/rules.d

（3）/etc/udev/rules.d

加载kernel模块的规则位于/lib/udev/rules.d/80-drivers.rules文件中，如下：

> ENV{MODALIAS}=="?\*", RUN{builtin}+="kmod load $env{MODALIAS}"

规则文件中的每一行都是由匹配规则加上执行动作组成。对于上面的例子，ENV{MODALIAS}=="?\*", 是匹配规则，RUN{builtin}+="kmod load $env{MODALIAS}"是执行动作。ENV用来匹配产生uevent的设备的MODALIAS属性，如果该设备对象定义了一个MODALIAS属性，并且不是空（？匹配一个字符，\*匹配0个或者多个字符），那么匹配成功，从而执行后面定义的动作。RUN就是定义执行的程序的，有两种情况，一种是外部的程序，其格式是RUN{program}，另外一种是build in在udev程序内部的命令，kmod是udev内嵌的加载内核模块的命令。

四、systemd如何处理和计算机网络相关的配置？

1、关于ifup和ifdown

ifup和ifdown是网络接口配置工具，它们会根据/etc/network/interfaces配置文件（该文件描述了本机如何连接到网络）对网络接口进行配置。具体interfaces的语法可以参考manual，我们这里结合一个实际的例子来说明。我们假设系统只有一个以太网接口连接到网络上，因此其interfaces文件如下：

> source /etc/network/interfaces.d/\*
>
> # The loopback network interface   
> auto lo   
> iface lo inet loopback
>
> # The primary network interface   
> allow-hotplug eth0   
> iface eth0 inet dhcp

source类似c语言中的include，可以把其他文件中的内容包括进来。auto和allow-hotplug都是配合ifup/ifdown命令的关键字。如果ifup命令行中传递的参数是-a的话，那么所有标注auto的网络接口都需要被up起来。如果ifup命令行中传递的参数是--allow=hotplug的话，那么所有标注allow-hotplug的网络接口都需要被up起来。

interfaces文件中的mapping关键字是用来将物理网卡接口（eth0）mapping到逻辑网卡接口上去的，一个物理网卡在不同的情况下可以有不同的逻辑网卡名字，听起来多酷啊，不过这和我们的场景无关，略过。iface关键字定义了逻辑网络接口极其配置，当然，如果没有定义mapping的话，其实逻辑网络接口等于物理网络接口。inet定义的是该网卡接口使用的address family，inet表示TCP/IP网络，使用IPV4的地址。最后一个dhcp说明eth0使用dhcp的方式获取IP地址。

2、什么服务会调用ifup来启用网卡接口呢？

在/lib/systemd/system目录下有一个[ifup@.service](mailto:ifup@.service)的文件，看起来应该是up网卡相关的服务，内容如下：

> [Unit]   
> Description=ifup for %I   
> After=local-fs.target network-pre.target networking.service   
> Before=network.target   
> BindsTo=sys-subsystem-net-devices-%i.device   
> ConditionPathIsDirectory=/run/network   
> DefaultDependencies=no
>
> [Service]   
> ExecStart=/sbin/ifup --allow=hotplug %I   
> ExecStop=/sbin/ifdown %I   
> RemainAfterExit=true

network.target是网络管理软件相关的服务，层次比较高，因此ifup service要Before network.target，After配置项的unit file列表是需要在ifup service之前完成的，ExecStart和ExecStop说明了该service需要调用的外部程序。

3、启动过程中，什么时候调用ifup来bring up网卡呢？

首先我们来看udev的配置文件，在/lib/udev/rules.d/80-networking.rules文件中有一句：

> SUBSYSTEM=="net", RUN+="net.agent"

如果内核发出的uevent中SUBSYSTEM是属于net类型的，那么就会调用net.agent来来处理该事件。对于支持hotplug的网络类型的设备，不论是插入还是拔出事件都会启动net.agent，对于插入事件，net.agent会调用ifup来启动该接口，对于拔出事件，net.agent会调用ifdown接口来disable该网络接口。上面说的是没有使用systemd的情况，如果使用了systemd，那么当网卡设备插入系统的时候，net.agent实际上会调用systemctl这个命令来start [ifup@xxx.service](mailto:ifup@xxx.service)，其中xxx是该网卡的名字。而[ifup@xxx.service](mailto:ifup@xxx.service)会通过[ifup@.service](mailto:ifup@.service)来启动ifup来启动所有标注allow-hotplug的网络接口。

五、自动启动wpa supplicant服务

1、关于wifi模块的加载

对于T450而言，使用的wifi设备可以通过lspci | grep Wireless这个命令看出来，输出如下：

> 03:00.0 Network controller: Intel Corporation Wireless 7265 (rev 61)

由此可知，T450使用的是Intel公司的7265 Wi-Fi Adapter模块。对于任何一个PCI设备，在PCI BUS这一个level上就会为每一个pci device增加MODALIAS这一个uevent变量（具体可以参考内核中pci\_uevent函数）。因此，这个Intel公司的7265 Wi-Fi Adapter模块在做为device插入设备模型的时候，实际上会把

MODALIAS=pci:v00008086d0000095Bsv00008086sd00005202bc02sc80i00

传递到用户空间去，而systemd会根据这个字符串来匹配对应的模块。alias和模块名字的对应关系保存在/lib/modules/xxxx/modules.alias文件中。通过查找，可以确定wifi模块的名字就是iwlwifi，然后在/lib/modules/3.16.0-4-amd64/kernel/drivers/net/wireless/iwlwifi目录下可以找到iwlwifi.ko文件。

虽然定位了最终的模块，不过并不是插入该模块就OK了，还需要处理依赖关系，所有iwlwifi.ko所依赖的模块也必须要插入到内核中，例如mac80211.ko模块，模块的依赖关系保存在modules.dep文件中。

2、启动wpa supplicant服务

当然，首先要写一个service文件wpa\_supplicant\_wlan0.service，如下：

> [Unit]   
> Description=WPA supplicant daemon (interface-specific version)   
> Requires=sys-subsystem-net-devices-wlan0.device   
> After=sys-subsystem-net-devices-wlan0.device   
> Before=network.target   
> Wants=network.target
>
> [Service]   
> Type=simple   
> ExecStart=/sbin/wpa\_supplicant -c/etc/wpa\_supplicant/wpa\_supplicant-wlan0.conf -Dnl80211 -iwlan0
>
> [Install]   
> [Alias=multi-user.target.wants/wpa\_supplicant\_wlan0.service](mailto:Alias=multi-user.target.wants/wpa_supplicant@.service)

我的T450只有一个wifi网卡，因此该wifi网卡的名字是wlan0。wpa supplicant服务启动起来有一个条件，那就是wifi网卡是ready的。对应我们的场景，当wpa supplicant service启动的时候，wlan0需要是ready的，否则该服务启动失败。配置文件中的Requires和After描述了这种依赖关系。虽然了解这个依赖关系，但是sys-subsystem-net-devices-wlan0.device是个什么鬼啊？其实.device是一种特殊的unit file，被称作device unit configuration file。基本上我们不需要手动写这个unit file，系统会自动创建。我们一起来看看/lib/udev/rules.d/目录下的99-systemd.rules文件，其中有这么一行：

> SUBSYSTEM=="net", KERNEL!="lo", TAG+="systemd", ENV{SYSTEMD\_ALIAS}+="/sys/subsystem/net/devices/$name"

所有标注了TAG+="systemd"的设备都会被system捕获到并创建对应的device unit file。因此，我们定义了wpa\_supplicant\_wlan0.service和wlan0这个设备的依赖关系，而systemd会在wlan0 ready之后再启动wpa supplicant服务。

有了service unit file还不行，我们需要把它挂入到启动过程中，以便在systemd从default.target执行初始化过程中，顺便将其启动起来，我们可以通过下面的命令完成该功能：

> sudo systemctl enable [wpa\_supplicant-wlan0.service](mailto:wpa_supplicant@.service)

执行该命令行会在/etc/systemd/system/multi-user.target.wants目录下面建一个符号连接。

3、分配IP地址

修改在/etc/network目录下的interface文件，增加下面的内容：

> allow-hotplug wlan0   
> iface wlan0 inet dhcp

重启计算，WiFi网卡可以自动的连接到AP并且自动获取IP地址，生活，就是这么美好。

*原创文章，转发请注明出处。蜗窝科技*
