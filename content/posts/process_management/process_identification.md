---
title: "process identification"
date: 2014-03-26T12:28:20+08:00
url: "/process_management/process_identification.html"
gid: "21"
emlog_type: "blog"
summary: "\r\n\t一、概述 \r\n\r\n\r\n\t本文主要描述在linux\r\nkernel中如何标识一个或者一组和进程（线程）相关的实体，包括： \r\n\r\n\r\n\t1、进程ID（线程组ID） \r\n\r\n\r\n\t2、线程ID \r\n\r\n\r\n\t3、进程组ID \r\n\r\n\r\n\t4、Session ID \r\n\r\n\r\n\t需要强调的是本文focus在identification，很多展开的内容会有一系列文档描述。 \r\n"
author: "linuxer"
category: "进程管理"
category_alias: "process_management"
tags: ["process", "management"]
views: 47533
comment_count: 9
aliases:
  - "/process_management/21.html"
  - "/21.html"
---

一、概述

本文主要描述在linux
kernel中如何标识一个或者一组和进程（线程）相关的实体，包括：

1、进程ID（线程组ID）

2、线程ID

3、进程组ID

4、Session ID

需要强调的是本文focus在identification，很多展开的内容会有一系列文档描述。

二、什么是进程ID（线程组ID）

一般而言，我们都会定义进程是一个正在执行的程序或者是一个程序的运行实例。程序是一个静态的概念，是存储在磁盘上的二进制可执行文件，包括程序代码和数据（正文段、数据段等）。当程序运行起来成为进程的时候，单纯的程序代码则不能清楚的描述进程，它还需要若干数据结构来描述程序的执行状态（硬件上下文和软件上下文）以及拥有的资源（如地址空间、打开的文件描述符等）。从内核的角度看，进程是一个和系统资源（CPU time、memory等）分配相关的实体。

在POSIX标准中，系统定义了getpid函数来获取一个进程的process ID。在linux kernel中，定义如下：

asmlinkage long sys\_getpid(void)

{

return
current->tgid;

}

从字面上看task\_struct中的tgid是thread group ID，也就是线程组ID，在linux kernel中，进程是有一个或者多个thread组成（POSIX规定多个thread要共享一个进程ID）。对于linux kernel，每一个thread分配一个task\_struct（其中有一个pid的标识），这和大部分的kernel处理不一样，其他的kernel针对一个进程分配一个task\_struct，在该task\_struct中嵌入了属于该进程的各个线程的数据。正因为如此，linux kernel创建一个线程组的概念来映射到POSIX中的进程概念。

多线程的进程中第一个线程（主线程，group leader）的pid等于tgid，之后，该线程组中的线程都有自己的pid，但是共享tgid，也就是传统意义上的进程ID。task\_struct有一个group\_leader成员，指向该task的thread group leader，对于group leader，该成员指向自己的task\_struct数据结构。

三、什么是线程ID

线程是进程中的一个实体，是被系统独立调度和分派的基本单位，线程自己不独立拥有系统资源，它是与同属一个进程的其它线程共享进程所拥有的全部资源（如地址空间、文件描述符和信号处理）。这首先表现在：所有线程都具有相同的地址空间（进程的地址空间），这意味着，线程可以访问该地址空间的每一个虚地址；此外，还可以访问进程所拥有的已打开文件、定时器、信号量等资源。进程是资源管理的最小单元，而线程是程序执行的最小单元。除了共享的进程资源，进程中的各个线程也属于自己的资源，具体包括：stack、PC counter和CPU寄存器。

每个线程应该有自己的ID，就是线程ID，在linux kernel中，每一个thread分配一个task\_struct，该结构中的pid成员就是线程ID。在POSIX标准中，定义了pthread\_self来获取线程ID，linux kernel采用了gettid的系统调用来获取调用者的线程ID。在linux kernel中，定义如下：

asmlinkage long sys\_gettid(void)

{

return
current->pid;

}

POSIX规定线程ID在所属进程中是唯一的，不过在linux
kernel的实现中，thread ID是全系统唯一的，当然，考虑到可移植性，Application
software不应该假设这一点。

四、什么是进程组ID

每个进程属于一个进程组，每个进程组有一个Leader进程，也就是进程ID等于进程组ID的那个进程。进程组有生命周期，它的生命周期开始于进程组leader创建进程组，结束于进程组内的最后一个进程离开进程组（可能是进程退出, 或加入其他进程组）。进程组概念的提出主要是由于：

1、和job control相关，关于job control，后续会专门的文档详细描述。

2、 Signal可以发送给进程组的每一个进程（job control也使用这个特性。例如job control signal会被送给job（进程组）中的每一个进程）

3、进程同步的时候，父进程可以wait for进程组中的任何一个进程

在POSIX标准中，系统定义了getpgid函数来获取一个进程的process group ID。在linux kernel中，定义如下：

asmlinkage long sys\_getpgid(pid\_t pid)

{

if
(!pid) {

//如果pid等于0，那么需要获取当前进程的进程组ID

return
process\_group(current);

}

else
{

//否则，获取pid标识的那个进程对应的进程组ID

int
retval;

struct
task\_struct \*p;

read\_lock(&tasklist\_lock);

p
= find\_task\_by\_pid(pid);

retval
= -ESRCH;

if
(p) {

//是否有权利获取其他进程的进程组ID

retval
= security\_task\_getpgid(p);

if
(!retval)

retval
= process\_group(p);

}

read\_unlock(&tasklist\_lock);

return
retval;

}

}

static inline pid\_t process\_group(struct
task\_struct \*tsk)

{

return
tsk->signal->pgrp;

}

task\_struct中的signal中的pgrp成员标识了进程组ID。从pgrp的位置来看，进程组应该是和信号处理相关的，后续会专门的文档详细描述。

五、Session ID

和进程属于进程组类似，每个进程组都属于一个session，每个session有一个Leader进程，也就是创建session的那个进程，session leader的ID就等于该session的ID。Session概念的提出和用户登录以及终端编程相关，后续会专门的文档详细描述。

在POSIX标准中，系统定义了getsid函数来获取session leader进程的process group ID。如果指定的PID不是session leader，将返回错误，但是在linux kernel中没有完全遵守这个规定，getsid函数总是能返回指定PID的session ID，无论该PID指向的进程是否是session leader，具体定义如下：

asmlinkage long sys\_getsid(pid\_t pid)

{

if
(!pid) {

//如果pid等于0，那么需要获取当前进程的进程组ID

return
process\_session(current);

}

else
{

//否则，获取pid标识的那个进程对应的进程组ID

int
retval;

struct
task\_struct \*p;

read\_lock(&tasklist\_lock);

p
= find\_task\_by\_pid(pid);

retval
= -ESRCH;

if
(p) {

retval
= security\_task\_getsid(p);

if
(!retval)

retval
= process\_session(p);

}

read\_unlock(&tasklist\_lock);

return
retval;

}

}

static inline pid\_t process\_session(struct
task\_struct \*tsk)

{

return
signal\_session(tsk->signal);

}

static inline pid\_t signal\_session(struct
signal\_struct \*sig)

{

return
sig->\_\_session;

}

task\_struct中的signal中的\_\_session成员标识了进程组ID。从\_\_session的位置来看，session应该也是和信号处理相关的，后续会详细描述。

*原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/forum/21.html)。*
