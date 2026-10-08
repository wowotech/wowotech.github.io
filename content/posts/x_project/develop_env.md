---
title: "X-000-PRE-开发环境搭建"
date: 2016-04-23T20:20:50+08:00
url: "/x_project/develop_env.html"
gid: "289"
emlog_type: "blog"
summary: "\r\n\t本文是“X Project”的第一篇文章，介绍怎么从零开始搭建“X \r\nProject”的开发环境（同样适用于其它的嵌入式Linux开发）。通过该过程，可以使读者对嵌入式Linux开发的基本流程有一个简单的了解，以达到“知其然、知其所以然”的目的。\r\n\r\n\r\n\t注1：有关“X Project”的介绍和讨论，可参考“/forum/"
author: "wowo"
category: "X Project"
category_alias: "x_project"
tags: ["x", "project", "git", "gerrit", "build", "environment"]
views: 19792
comment_count: 31
aliases:
  - "/x_project/289.html"
  - "/289.html"
---

#### 1. 前言

本文是“X Project”的第一篇文章，介绍怎么从零开始搭建“X Project”的开发环境（同样适用于其它的嵌入式Linux开发）。通过该过程，可以使读者对嵌入式Linux开发的基本流程有一个简单的了解，以达到“知其然、知其所以然”的目的。

注1：有关“X Project”的介绍和讨论，可参考“[/forum/](/forum/2.html)”。

#### 2. 文章命名规则

由于项目会发布很多文章，为了方便大家阅读，制订了一个简单的规则，即“项目代码-编号-模块名-文章名”这样的四段编码：

> 项目代码，识别特定的项目，对“X Project”来说，代码为“X”；
>
> 编号，是一个3位的十进制数，如000,001等，用来标示先后顺序；
>
> 模块名用于区分涉及到的功能模块，初步计划有如下模块：PRE（开发前的准备阶段，如开发环境等）；UBOOT；KERNEL；ROOTFS；DEBIAN；UBUNTU；ANDROID，后续如果有需要，会再增加。
>
> 文章名，本篇文章的描述。

#### 3. 开发环境组成

如今的嵌入式Linux开发，涉及如下的开发环境：

[![开发过程](/content/uploadfile/201604/f4dec8e613be29f51d924f470d23134420160423122049.gif "开发过程")](/content/uploadfile/201604/7772fd233effde5d0036ee7f5e778c5920160423122048.gif)

图片1 嵌入式Linux开发环境组成

1）Internet

这是一个open source的时代，linux kernel又是open source的典型代表，因此，Linux相关的开发工作，一定不能离开互联网：

> 在“X Project”的初期阶段，我们会从Internet搜集各种开源软件，如U-boot、Linux kernel等，作为我们开发的基准；
>
> 在“X Project”的开发阶段，我们会从Internet查阅知识、讨论问题，并将阶段性的成果分享出来；
>
> 等等。

2）Code server & Code review server

Linux相关的开发工作，涉及到非常庞大的代码量，u-boot、kernel、android等等，同时又是多人协同工作，因而需要一台服务器以及相应的版本管理工具管理这些代码，这就是代码服务器（code server）。得益于open source的力量，提供了免费的Git（版本管理工具）以及github[1]（代码服务器），我们就恭敬不如从命了。

与此同时，为了提高代码质量，提交到代码服务器的代码，需要经过多人的审核，才能最终被接受，这就是代码审核服务器的作用（code review server）。同样，我们有强大的open source，可以使用免费的Gerrit（代码审核工具）以及gerrithub[2]（代码审核服务器）。

注2：代码审核的过程，也是一个互相学习、互相提高的过程，希望大家能够重视，积极参与。

3）Build server

编译服务器（Build server）负责把程序员语言（汇编/C/C++等）转换为机器语言。由于代码量庞大，编译的过程非常消耗CPU和memory资源（换句话说，耗钱！），所以，再伟大的open source，在钱面前，都麻烦了，结果是我们没有免费的编译服务器可供使用。

通常情况下，在公司环境中，会有几台专用的PC（或server），当作编译服务器，负责代码的编译工作。但是在开放社区（例如我们的“X Project”），由于条件有限，大家只能使用个人的PC，作为编译服务器。

4）Host

Host是我们日常工作用的PC，在开发过程中，负责如下事项：

> 登陆到Build server，进行代码的下载、编译、上传等工作（如果PC就是build server，则省略登陆的过程）；
>
> 上网查阅资料；
>
> 和小伙伴们交流、讨论、沟通；
>
> 文档的记录和整理；
>
> 和Target交互，进行固件更新、状态监控、调试、测试等工作。

5）Target

Target是嵌入式Linux运行的目标硬件平台，例如开发板、手机等。Target可以联网，可以在项目开发的初期通过Uart、USB等和Host通信。

#### 4. 开发步骤

“X Project”的开发步骤总结如下：

1）准备工作，包括：

> Target、Host、Build server、Code server、Code review server的准备；
>
> 初始化Code server，确定基本的目录结构；
>
> 从开源社区import基础的开源软件，当前主要包括u-boot和kernel。

2）代码下载

3）设计、coding、编译

4）将编译结果放到Target中运行

5）将改动提交到代码审核服务器审核

6）如果审核不通过，继续步骤3~5

7）如果审核通过，自动merge到代码服务器

8）重复步骤3~7，直至取得阶段性的成果

9）将阶段性成果push到开源社区，然后重复步骤3~8，直至项目完成

#### 5 开发环境搭建

##### 5.1 Target

由“[关于“X Project”](/forum/2.html)”的可知，“X Project”对Target没有要求，大家手边的开发板、旧手机等设备，只要满足如下的条件，就可以使用：

> 功能正常；
>
> 有简单的硬件资料；
>
> 有简单的原理图；
>
> 能否从USB、SD/MMC卡、U盘等任意一种介质启动。

##### 5.2 Host和Buid server

Host和Build server可以是同一台PC（相信大部分人都是如此），也可以使用多台PC。Host没有特殊要求，Windows系统或者Linux都OK。但Build server一定要选用Linux环境，有三种方案：

> 1）Linux OS（如Ubuntu、Debian等）。
>
> 2）Windows OS，使用虚拟机（VMware或者VirtualBox）运行Linux OS（Ubuntu、Debian等）。
>
> 3）Windows OS，使用Cygwin、MSYS2等GNU模拟器，模拟Linux环境（使用这种方法的时候，需要特别注意，Linux kernel的source code中，同一个目录下存在两个名称相同、只有大小写不同的文件，而Windows系统不区分大小写，因而会出现问题）。

Build server应安装代码编译所需基本工具，如git、make、binutils、make、交叉编译工具等。有关Build server的大家，本文不再详细介绍（相信大家的折腾能力），如有需要，后面会使用单独的文章描述。

##### 5.3 Code server

###### 5.3.1 github

我们使用github作为code server，相关的步骤包括：

1）注册github账号并登陆。

2）创建一个组织（organizations），用来将该项目的多个代码仓库分组（group）。

> 创建组织的链接如下：[https://github.com/account/organizations/new](https://github.com/account/organizations/new "https://github.com/account/organizations/new")
>
> 最终“X Project”所在的组织地址为：[https://github.com/wowotechX](https://github.com/wowotechX "https://github.com/wowotechX")
>
> 具体的创建步骤不再详细介绍，大家如有疑问，可以论坛中提问。

注3：github没有为代码仓库（repository）提供分组功能，如果账号下面创建、clone的仓库过多，Dashboard下面会存在长长的一串仓库列表，非常不便。再加上如果有些仓库名类似的话，就更麻烦了。这个问题可以借助github的organizations功能解决（organizations的初衷并不是做这个事情），即为每一个项目，创建一个organizations，该organizations下所有的仓库独立分组（类似于一个目录）。

###### 5.3.2 代码仓库的规划

“X Project”暂时提供如下的仓库（repository），后续会根据需要新增：

> u-boot，基于最新版本的u-boot开发，提供bootloader的功能；
>
> linux，基于最新版本的kernel开发，会在某一个时间的，rebase到为了一个long team的kernel上；
>
> build，提供代码编译相关的工具、脚本等，暂时包括如下目录：   
>  tools，各个平台的交叉编译工具；   
>  scripts，一些方便的编译脚本。
>
> tools，编译之外的工具支持，如固件的打包、添加header等，暂时包括如下目录：   
>  common，通用工具及其Makefile文件；   
>  xxx，某个芯片厂商有关的特定目录（例如有些芯片需要为boot image添加特定的header等）。

###### 5.3.3 代码仓库的初始化

1）新建u-boot repository，并从官网导入当前版本

> 新建repository的链接为：[https://github.com/organizations/wowotechX/repositories/new](https://github.com/organizations/wowotechX/repositories/new "https://github.com/organizations/wowotechX/repositories/new")
>
> 创建成功后的repository地址为：[https://github.com/wowotechX/u-boot](https://github.com/wowotechX/u-boot "https://github.com/wowotechX/u-boot")
>
> 通过repository页面底部的import按钮，可以从外部导入代码：   
>  导入的链接为：[https://import.github.com/wowotechX/u-boot/import](https://import.github.com/wowotechX/u-boot/import "https://import.github.com/wowotechX/u-boot/import")  
>  可以从u-boot的官方仓库导入：git://git.denx.de/u-boot.git   
>  填入地址后，github会自动导入，关闭浏览器，睡觉去吧，等待导入完成即可。

注4：代码导入完成后，该仓库所有的分支、提交记录等信息，都会保留，通过git命令即可查看。

2）从Linus的github clone当前版本的linux的kernel

j经过实践，发现采用import的方式，无法成功导入linux kernel，因此这里直接从Linus的github clone，源地址为：

> [https://github.com/torvalds/linux](https://github.com/torvalds/linux "https://github.com/torvalds/linux")

clone后位于的地址为：

> [https://github.com/wowotechX/linux](https://github.com/wowotechX/linux "https://github.com/wowotechX/linux")

注5：使用mainline版本不一定稳定的，不过没关系，后续r我们可以ebase到一个稳定的long team版本上，顺便练习下git的使用。

3）新建build和tools两个仓库，并进行必要的初始化

结果如下（子目录暂未创建，后续在用到的时候，会通过git命令创建）：

[https://github.com/wowotechX/build](https://github.com/wowotechX/build "https://github.com/wowotechX/build")

[https://github.com/wowotechX/tools](https://github.com/wowotechX/tools "https://github.com/wowotechX/tools")

##### 5.4 Code review server

TODO，后续会通过专门的文章，介绍基于gerrithub的代码审核方法。

#### 6 总结

本文完成了“X Project”开发环境的搭建工作，后续还会有两篇作为补充的文章，包括：

> [X-001-PRE-git介绍及操作记录](/x_project/git_record.html)，用于记录X Project有关的git操作命令，通过实践的方式，学习、理解并掌握git的使用；
>
> X-002-PRE-基于Gerrithub的代码审核环境的创建及使用指南，介绍基于gerrithub搭建代码审核服务器的过程，及代码审核的方法和流程。

#### 7 参考文档

[1] github，基于Git的代码服务器，[www.github.com](http://www.github.com)

[2] gerrithub，基于Gerrit的代码审核服务器，[www.gerrithub.io](http://www.gerrithub.io)

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/x_project/develop_env.html)。
