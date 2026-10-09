---
title: "Linux时间子系统之（三）：用户空间接口函数"
date: 2014-12-24T15:48:59+08:00
url: "/timer_subsystem/timer_subsystem_userspace.html"
gid: "130"
emlog_type: "blog"
summary: "从应用程序的角度看，内核需要提供的和时间相关的服务有三种： 1、和系统时间相关的服务。例如，在向数据库写入一条记录的时候，需要记录操作时间（何年何月何日何时）。 2、让进程睡眠一段时间 3、和timer相关的服务。在一段指定的时间过去后，kernel要alert用户进程 本文主要描述和时间子系统相关的用户空间接口函数知识。"
author: "linuxer"
category: "时间子系统"
category_alias: "timer_subsystem"
tags: ["Linux时间子系统用户空间接口函数"]
views: 43539
comment_count: 19
aliases:
  - "/timer_subsystem/130.html"
  - "/130.html"
---

一、前言

从应用程序的角度看，内核需要提供的和时间相关的服务有三种：

1、和系统时间相关的服务。例如，在向数据库写入一条记录的时候，需要记录操作时间（何年何月何日何时）。

2、让进程睡眠一段时间

3、和timer相关的服务。在一段指定的时间过去后，kernel要alert用户进程

本文主要描述和时间子系统相关的用户空间接口函数知识。

二、和系统时间相关的服务

1、秒级别的时间函数：time和stime

time和stime函数的定义如下：

> #include <time.h>
>
> time\_t time(time\_t \*t);
>
> int stime(time\_t \*t);

time函数返回了当前时间点到linux epoch的秒数（内核中timekeeper模块保存了这个值，timekeeper->xtime\_sec）。stime是设定当前时间点到linux epoch的秒数。对于linux kernel，设定时间的进程必须拥有CAP\_SYS\_TIME的权利，否则会失败。

linux kernel用系统调用sys\_time和sys\_stime来支持这两个函数。实际上，在引入更高精度的时间相关的系统调用之后（例如：sys\_gettimeofday），上面这两个系统调用可以用新的系统调在用户空间实现time和stime函数。在kernel中，只有定义了\_\_ARCH\_WANT\_SYS\_TIME这个宏，系统才会提供上面这两个系统调用。当然，提供这样的系统调用多半是为了兼容旧的应用软件。

配合上面的接口函数还有一系列将当前时间点到linux epoch的秒数转换成适合人类阅读的接口函数，例如asctime, ctime, gmtime, localtime, mktime, asctime\_r, ctime\_r, gmtime\_r, localtime\_r ，这些函数主要用来将time\_t类型的时间转换成break-down time或者字符形式。

2、微秒级别的时间函数：gettimeofday和settimeofday

> #include <sys/time.h>
>
> int gettimeofday(struct timeval \*tv, struct timezone \*tz);
>
> int settimeofday(const struct timeval \*tv, const struct timezone \*tz);

这两个函数和上一小节秒数的函数类似，只不过时间精度可以达到微秒级别。gettimeofday函数可以获取从linux epoch到当前时间点的秒数以及微秒数（在内核态，这个时间值仍然是通过timekeeper模块获得的，具体接口是getnstimeofday64，该接口的时间精度是纳秒级别的，不过没有关系，除以1000就获得微秒级别的精度了），settimeofday则是设定从linux epoch到当前时间点的秒数以及微秒数。同样的，设定时间的进程必须拥有CAP\_SYS\_TIME的权利，否则会失败。tz参数是由于历史原因而存在，实际上内核并没有对timezone进行支持。

显然，sys\_gettimeofday和sys\_settimeofday这两个系统调用是用来支持上面两个函数功能的，值得一提的是：这些系统调用在新的POSIX标准中 gettimeofday和settimeofday接口函数被标注为obsolescent，取而代之的是clock\_gettime和clock\_settime接口函数

3、纳秒级别的时间函数：clock\_gettime和clock\_settime

> #include <time.h>
>
> int clock\_getres(clockid\_t clk\_id, struct timespec \*res);
>
> int clock\_gettime(clockid\_t clk\_id, struct timespec \*tp);
>
> int clock\_settime(clockid\_t clk\_id, const struct timespec \*tp);

如果不是clk\_id这个参数，clock\_gettime和clock\_settime基本上是不用解释的，其概念和gettimeofday和settimeofday接口函数是完全类似的，除了精度是纳秒。clock就是时钟的意思，它记录了时间的流逝。clock ID当然就是识别system clock（系统时钟）的ID了，定义如下：

> CLOCK\_REALTIME   
> CLOCK\_MONOTONIC   
> CLOCK\_MONOTONIC\_RAW   
> CLOCK\_PROCESS\_CPUTIME\_ID   
> CLOCK\_THREAD\_CPUTIME\_ID

根据应用的需求，内核维护了几个不同系统时钟。大家最熟悉的当然就是CLOCK\_REALTIME这个系统时钟，因为它表示了真实世界的墙上时钟（前面两节的接口函数没有指定CLOCK ID，实际上获取的就是CLOCK\_REALTIME的时间值）。CLOCK\_REALTIME这个系统时钟允许用户对其进行设定（当然要有CAP\_SYS\_TIME权限），这也就表示在用户空间可以对该系统时钟进行修改，产生不连续的时间间断点。除此之外，也可以通过NTP对该时钟进行调整（不会有间断点，NTP调整的是local oscillator和上游服务器频率误差而已）。

仅仅从名字上就可以看出CLOCK\_MONOTONIC的系统时钟应该是单调递增的，此外，该时钟也是真实世界的墙上时钟，只不过其基准点不一定是linux epoch（当然也可以是），一般会把系统启动的时间点设定为其基准点。随后该时钟会不断的递增。除了可以通过NTP对该时钟进行调整之外，其他任何程序不允许设定该时钟，这样也就保证了该时钟的单调性。

CLOCK\_MONOTONIC\_RAW具备CLOCK\_MONOTONIC的特性，除了NTP调整。也就是说，clock id是CLOCK\_MONOTONIC\_RAW的系统时钟是一个完全基于本地晶振的时钟。不能设定，也不能对对晶振频率进行调整。

在调用clock\_gettime和clock\_settime接口函数时，如果传递clock id参数是CLOCK\_REALTIME的话，那么这两个函数的行为和前两个小节描述的一致，除了是ns精度。读到这里，我详细广大人民群众不免要问：为何要有其他类型的系统时钟呢？MONOTONIC类型的时钟相对比较简单，如果你设定事件A之后5秒进行动作B，那么用MONOTONIC类型的时钟是一个比较好的选择，如果使用REALTIME的时钟，当用户在事件A和动作B之间插入时间设定的操作，那么你设定事件A之后5秒进行动作B将不能触发。此外，用户需要了解系统启动时间，这个需求需要使用MONOTONIC类型的时钟的时钟。需要指出的是MONOTONIC类型的时钟不是绝对时间的概念，多半是计算两个采样点之间的时间，并且保证采样点之间时间的单调性。MONOTONIC\_RAW是一个底层工具，一般而言程序员不会操作它，使用MONOTONIC类型的时钟就够用了，当然，一些高级的应用场合，例如你想使用另外的方法（不是NTP）来调整时间，那么就可以使用MONOTONIC\_RAW了。

有些应用场景使用real time的时钟（墙上时钟）是不合适的，例如当我们进行系统中各个应用程序的性能分析和统计的时候。正因为如此，kernel提供了基于进程或者线程的系统时钟，也就是CLOCK\_PROCESS\_CPUTIME\_ID和CLOCK\_THREAD\_CPUTIME\_ID了。当我们打算使用基于进程或者线程的系统时钟的时候，需要首先获取clock id：

> #include <time.h>
>
> int clock\_getcpuclockid(pid\_t pid, clockid\_t \*clock\_id);

如果是线程的话，需要调用pthread\_getcpuclockid接口函数：

> #include <pthread.h>   
> #include <time.h>
>
> int pthread\_getcpuclockid(pthread\_t thread, clockid\_t \*clock\_id);

虽然这组函数接口的精度可以达到ns级别，但是实际的系统可以达到什么样的精度是实现相关的，因此，clock\_getres用来获取系统时钟的精度。

4、系统时钟的调整

设定系统时间是一个比较粗暴的做法，一旦修改了系统时间，系统中的很多依赖绝对时间的进程会有各种奇奇怪怪的行为。正因为如此，系统提供了时间同步的接口函数，可以让外部的精准的计时服务器来不断的修正系统时钟。

（1）adjtime接口函数

> int adjtime(const struct timeval \*delta, struct timeval \*olddelta);

该函数可以根据delta参数缓慢的修正系统时钟（CLOCK\_REALTIME那个）。olddelta返回上一次调整中尚未完整的delta。

（2）adjtimex

> #include <sys/timex.h>
>
> int adjtimex(struct timex \*buf);

RFC 1305定义了更复杂，更强大的时间调整算法，因此linux kernel通过sys\_adjtimex支持这个算法，其用户空间的接口函数就是adjtimex。由于这个算法过去强大，这里就不再赘述，等有时间、有兴趣之后再填补这里的空白吧。

Linux内核提供了sys\_adjtimex系统调用来支持上面两个接口函数。此外，还提供了sys\_clock\_adjtime的系统调用来支持POSIX clock tunning。

三、进程睡眠

1、秒级别的sleep函数：sleep

> #include <unistd.h>
>
> unsigned int sleep(unsigned int seconds);

调用该函数会导致当前进程sleep，seconds之后（基于CLOCK\_REALTIME）会返回继续执行程序。该函数的返回值说明了进程没有进入睡眠的时间。例如如果我们想要睡眠8秒，但是由于siganl中断了睡眠，只是sleep了5秒，那么返回值就是3，表示有3秒还没有睡。

2、微秒级别的sleep函数：usleep

> #include <unistd.h>
>
> int usleep(useconds\_t usec);

概念上和sleep一样，不过返回值的定义不同。usleep返回0表示执行成功，返回-1说明执行失败，错误码在errno中获取。

3、纳秒级别的sleep函数：nanosleep

> #include <time.h>
>
> int nanosleep(const struct timespec \*req, struct timespec \*rem);

usleep函数已经是过去式，不建议使用，取而代之的是nanosleep函数。req中设定你要sleep的秒以及纳秒值，然后调用该函数让当前进程sleep。返回0表示执行成功，返回-1说明执行失败，错误码在errno中获取。EINTR表示该函数被signal打断。rem参数是remaining time的意思，也就是说还有多少时间没有睡完。

linux kernel并没有提供sleep和usleep对应的系统调用，sleep和usleep的实现位于c lib。在有些系统中，这些实现是依赖信号的，也有的系统使用timer来实现的，对于GNU系统，sleep和usleep和nanosleep函数一样，都是通过kernel的sys\_nanosleep的系统调用实现的（底层是基于hrtimer）。

4、更高级的sleep函数：clock\_nanosleep

> #include <time.h>
>
> int clock\_nanosleep(clockid\_t clock\_id, int flags,   
> const struct timespec \*request,   
> struct timespec \*remain);

clock\_nanosleep接口函数需要传递更多的参数，当然也就是意味着它功能更强大。clock\_id说明该接口函数不仅能基于real time clock睡眠，还可以基于其他的系统时钟睡眠。flag等于0或者1，分别指明request参数设定的时间值是相对时间还是绝对时间。

四、和timer相关的服务

1、alarm函数

> #include <unistd.h>
>
> unsigned int alarm(unsigned int seconds);

alarm函数是使用timer最简单的接口。在指定秒数（基于CLOCK\_REALTIME）的时间过去后，向该进程发送SIGALRM信号。当然，调用该接口的程序需要设定signal handler。

2、Interval timer函数

> #include <sys/time.h>
>
> int getitimer(int which, struct itimerval \*curr\_value);   
> int setitimer(int which, const struct itimerval \*new\_value,   
> struct itimerval \*old\_value);

Interval timer函数的行为和alarm函数类似，不过功能更强大。每个进程支持3种timer，不同的timer定义了如何计时以及发送什么样的信号给进程，which参数指明使用哪个timer：

（1）ITIMER\_REAL。基于CLOCK\_REALTIME计时，超时后发送SIGALRM信号，和alarm函数一样。

（2）ITIMER\_VIRTUAL。只有当该进程的用户空间代码执行的时候才计时，超时后发送SIGVTALRM信号。

（3）ITIMER\_PROF。只有该进程执行的时候才计时，不论是执行用户空间代码还是陷入内核执行（例如系统调用），超时后发送SIGPROF信号。

struct itimerval定义如下：

> struct itimerval {   
> struct timeval it\_interval; /\* next value \*/   
> struct timeval it\_value; /\* current value \*/   
> };

两个成员分别指明了本次和下次（超期后如何设定）的时间值。通过这样的定义，interval timer可以实现one shot类型的timer和periodic的timer。例如current value设定为5秒，next value设定为3秒，设定这样的timer后，it\_value值会不断递减，直到5秒后触发，而随后it\_value的值会被重新加载（使用it\_interval的值），也就是等于3秒，之后会按照3为周期不断的触发。

old\_value返回上次setitimer函数的设定值。getitimer函数获取当前的Interval timer的状态，其中的it\_value成员可以得到当前时刻到下一次触发点的世时间信息，it\_interval成员保持不变，除非你重新调用setitimer重新设定。

虽然interval timer函数也是POSIX标准的一部分，不过在新的POSIX标准中，interval timer接口函数被标注为obsolescent，取而代之的是POSIX timer接口函数。

3、更高级，更灵活的timer函数

上一节介绍的Interval timer函数还是有功能不足之处：例如一个进程只能有ITIMER\_REAL、ITIMER\_VIRTUAL和ITIMER\_PROF三个timer，如果连续设定其中一种timer（例如ITIMER\_REAL），这会导致第一个设定被第二次设定覆盖。此外，超时处理永远是用信号的方式，而且发送的signal不能修改。当mask信号处理的时候，虽然timer多次超期，但是signal handler只会调用一次，无法获取更详细的信息。最后一点，Interval timer函数精度是微秒级别，精度有进一步提升的空间。正因为传统的Interval timer函数的不足之处，POSIX标准定义了更高级，更灵活的timer函数，我们称之POSIX （interval）Timer。

（1）创建timer

> #include  <signal.h>  
> #include <time.h>
>
> int timer\_create(clockid\_t clockid, struct sigevent \*sevp, timer\_t \*timerid);

在这个接口函数中，clock id相信大家都很熟悉了， timerid一看就是返回的timer ID的句柄，就像open函数返回的文件描述符一样。因此，要理解这个接口函数重点是了解struct sigevent这个数据结构：

> union sigval { /\* Data passed with notification \*/   
> int sival\_int; /\* Integer value \*/   
> void \*sival\_ptr; /\* Pointer value \*/   
> };
>
> typedef struct sigevent {   
> sigval\_t sigev\_value;   
> int sigev\_signo;   
> int sigev\_notify;   
> union {   
> int \_pad[SIGEV\_PAD\_SIZE];   
> int \_tid;
>
> struct {   
> void (\*\_function)(sigval\_t);   
> void \*\_attribute; /\* really pthread\_attr\_t \*/   
> } \_sigev\_thread;   
> } \_sigev\_un;   
> } sigevent\_t;

sigev\_notify定义了当timer超期后如何通知该进程，可以设定：

（a）SIGEV\_NONE。不需要异步通知，程序自己调用timer\_gettime来轮询timer的当前状态

（b）SIGEV\_SIGNAL。使用sinal这样的异步通知方式。发送的信号由sigev\_signo定义。如果发送的是realtime signal，该信号的附加数据由sigev\_value定义。

（c）SIGEV\_THREAD。创建一个线程执行timer超期callback函数，\_attribute定义了该线程的属性。

（d）SIGEV\_THREAD\_ID。行为和SIGEV\_SIGNAL类似，不过发送的信号被送达进程内的一个指定的thread，这个thread由\_tid标识。

（2）设定timer

> #include <time.h>
>
> int timer\_settime(timer\_t timerid, int flags, const struct itimerspec \*new\_value,   
> struct itimerspec \* old\_value);   
> int timer\_gettime(timer\_t timerid, struct itimerspec \*curr\_value);

timerid就是上一节中通过timer\_create创建的timer。new\_value和old\_value这两个参数类似setitimer函数，这里就不再细述了。flag等于0或者1，分别指明new\_value参数设定的时间值是相对时间还是绝对时间。如果new\_value.it\_value是一个非0值，那么调用timer\_settime可以启动该timer。如果new\_value.it\_value是一个0值，那么调用timer\_settime可以stop该timer。

timer\_gettime函数和getitimer类似，可以参考上面的描述。

（3）删除timer

> #include <time.h>
>
> int timer\_delete(timer\_t timerid);

有创建就有删除，timer\_delete用来删除指定的timer，释放资源。

*原创文章，转发请注明出处。蜗窝科技*

[/timer_subsystem/timer_subsystem_userspace.html](/timer_subsystem/timer_subsystem_userspace.html)
