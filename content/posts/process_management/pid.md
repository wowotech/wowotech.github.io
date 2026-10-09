---
title: "Linux系统如何标识进程？"
date: 2017-02-23T19:10:26+08:00
url: "/process_management/pid.html"
gid: "378"
emlog_type: "blog"
summary: "其实两年前，本站已经有了一篇关于 进程标识 的文档，不过非常的简陋，而且代码是来自2.6内核。随着linux container、pid namespace等概念的引入，进程标识方面已经有了天翻地覆的变化，因此我们需要对这部分的内容进行重新整理。 本文主要分成四个部分来描述进程标识这个主题：在初步介绍了一些入门的各种IDs基础知识后，在第三章我们描述了pid、pid number、pid name"
author: "linuxer"
category: "进程管理"
category_alias: "process_management"
tags: ["进程ID"]
views: 19173
comment_count: 3
aliases:
  - "/process_management/378.html"
  - "/378.html"
---

一、前言

其实两年前，本站已经有了一篇关于[进程标识](/process_management/process_identification.html)的文档，不过非常的简陋，而且代码是来自2.6内核。随着linux container、pid namespace等概念的引入，进程标识方面已经有了天翻地覆的变化，因此我们需要对这部分的内容进行重新整理。

本文主要分成四个部分来描述进程标识这个主题：在初步介绍了一些入门的各种IDs基础知识后，在第三章我们描述了pid、pid number、pid namespace等基础的概念。第四章重点描述了内核如何将这些基本概念抽象成具体的数据结构，最后我们简单分析了内核关于进程标识的源代码（代码来自linux4.4.6版本）。

二、各种ID概述

所谓进程其实就是执行中的程序而已，和静态的程序相比，进程是一个运行态的实体，拥有各种各样的资源：地址空间（未必使用全部地址空间，而是排布在地址空间上的一段段的memory mappings）、打开的文件、pending的信号、一个或者多个thread of execution，内核中数据实体（例如一个或者多个task\_struct实体），内核栈（也是一个或者多个）等。针对进程，我们使用进程ID，也就是pid（process ID）。通过getpid和getppid可以获取当前进程的pid以及父进程的pid。

进程中的thread of execution被称作线程（thread），线程是进程中活跃状态的实体。一方面进程中所有的线程共享一些资源，另外一方面，线程又有自己专属的资源，例如有自己的PC值，用户栈、内核栈，有自己的hw context、调度策略等等。我们一般会说进程调度什么的，但是实际上线程才是是调度器的基本单位。对于Linux内核，线程的实现是一种特别的存在，和经典的unix都不一样。在linux中并不区分进程和线程，都是用task\_struct来抽象，只不过支持多线程的进程是由一组task\_struct来抽象，而这些task\_struct会共享一些数据结构（例如内存描述符）。我们用thread ID来唯一标识进程中的线程，POSIX规定线程ID在所属进程中是唯一的，不过在linux kernel的实现中，thread ID是全系统唯一的，当然，考虑到可移植性，Application software不应该假设这一点。在用户空间，通过gettid函数可以获取当前线程的thread ID。对于单线程的进程，process ID和thread ID是一样的，对于支持多线程的进程，每个线程有自己的thread ID，但是所有的线程共享一个PID。

为了方便shell进行Job controll，我们需要把一组进程组织起来形成进程组。关于这方面的概念，在[进程和终端](/process_management/process-tty-basic.html)文档中描述的很详细，这里就不赘述了。为了标识进程组，我们需要引入进程组ID的概念。我们一般把进程组中的第一个进程的ID作为进程组的ID，进程组中的所有进程共享一个进程组ID。在用户空间，通过setpgid、getpgid、setpgrp和getpgrp等接口函数可以访问process group ID。

经过thread ID、process ID、process group ID的层层递进，我们终于来到最顶层的ID，也就是session ID，这个ID实际上是用来标识计算机系统中的一次用户交互过程：用户登录入系统，不断的提交任务（即Job或者说是进程组）给计算机系统并观察结果，最后退出登录，销毁该session。关于session的概念，在[进程和终端](/process_management/process-tty-basic.html)文档中描述的也很详细，大家可以参考那份文档，这里就不赘述了。在用户空间，我们可以通过getsid、setsid来操作session ID。

三、基础概念

1、用户空间如何看到process ID

我们用下面这个block diagram来描述用户空间和内核空间如何看待process ID的：

[![getpid](/content/uploadfile/201702/5f093198ce1a99e8c632b2cf0e47355320170223111014.gif "getpid")](/content/uploadfile/201702/122dff61618dc06cc1fec3649030d47f20170223111013.gif)

从用户空间来看，每一个进程都可以调用getpid来获取标识该进程的ID，我们称之PID，其类型是pid\_t。因此，我们知道在用户空间可以通过一个正整数来唯一标识一个进程（我们称这个正整数为pid number）。在引入容器之后，事情稍微复杂一点，pid这个正整数只能是唯一标识容器内的进程。也就是说，如果有容器1和容器2存在于系统中，那么可以同时存在两个pid等于a的进程，分别位于容器1和容器2。当然，进程也可以不在容器里，例如进程x和进程y，它们就类似传统的linux系统中的进程。当然，你也可以认为进程x和进程y位于一个系统级别的顶层容器0，其中包括进程x和进程y以及两个容器。同样的概念，容器2中也可以嵌套一个容器，从而形成了一个container hierarchy。

容器（linux container）是一个OS级别的虚拟化方法，基本上是属于纯软件的方法来实现虚拟化，开销小，量级轻，当然也有自己的局限。linux container主要应用了内核中的cgroup和namespace隔离技术，当然这些内容不是我们这份文档关心的，我们这里主要关心pid namespace。

当一个进程运行在linux OS之上的时候，它拥有了很多的系统资源，例如pid、user ID、网络设备、协议栈、IP以及端口号、filesystem hierarchy。对于传统的linux，这些资源都是全局性的，一个进程umount了某一个文件系统挂载点，改变了自己的filesystem hierarchy视图，那么所有进程看到的文件系统目录结构都变化了（umount操作被所有进程感知到了）。有没有可能把这些资源隔离开呢？这就是namespace的概念，而PID namespace就是用来隔离pid的地址空间的。

进程是感知不到pid namespace的，它只是知道能够通过getpid获取自己的ID，并不知道自己实际上被关在一个pid namespace的牢笼。从这个角度看，用户空间是简单而幸福的，内核空间就没有这么幸运了，我们需要使用复杂的数据结构来抽象这些形成层次结构的PID。

最后顺便说一句，上面的描述是针对pid而言的，实际上，tid、pgid和sid都是一样的概念，原来直接使用这些ID就可以唯一标识一个实体，现在我们需要用（pid namespace，ID）来唯一标识一个实体。

2、内核空间如何看到process ID

虽然从用户空间看，一个pid用一个正整数表示就足够了，但是在内核空间，一个正整数肯定是不行的，我们用一个2个层次的pid namespace来描述（也就是上面图片的情形）。pid namespace 0是pid namespace 1和2的parent namespace，在pid namespace 1中的pid等于a的那进程，对应pid namespace 0中的pid等于m的那进程，也就是说，内核态实际需要两个不同namespace中的正整数来记录一个进程的ID信息。推广开来，我们可以这么描述，在一个n个level的pid namespace hieraray中，位于x level的进程需要x个正整数ID来表示该该进程。

除此之外，内核还有记录pid namespace之间的关系：谁是根，谁是叶，父子关系……

四、内核态的数据抽象

1、如何抽象pid number？

> struct upid {   
> int nr;   
> struct pid\_namespace \*ns;   
> struct hlist\_node pid\_chain;   
> };

虽然用户空间使用一个正整数来表示各种IDs，但是对于内核，我们需要使用（pid namespace，ID number）这样的二元组来表示，因为单纯的pid number是没有意义的，必须限定其pid namespace，只有这样，那个ID number才是唯一的。这样，upid中的nr和ns成员就比较好理解了，分别对应ID number和pid namespace。此外，当userspace传递ID number参数进入内核请求服务的时候（例如向某一个ID发送信号），我们必须需要通过ID number快速找到其对应的upid数据对象，为了应对这样的需求，内核将系统内所有的upid保存在哈希表中，pid\_chain成员是哈希表中的next node。

2、如何抽象tid、pid、sid、pgid？

> struct pid   
> {   
> atomic\_t count;   
> unsigned int level;   
> struct hlist\_head tasks[PIDTYPE\_MAX];   
> struct rcu\_head rcu;   
> struct upid numbers[1];   
> };

虽然其名字是pid，不过实际上这个数据结构抽象了不仅仅是一个thread ID或者process ID，实际上还包括了进程组ID和session ID。由于多个task struct会共享pid（例如一个session中的所有的task struct都会指向同一个表示该session ID的struct pid数据对象），因此存在count这样的成员也就不奇怪了，表示该数据对象的引用计数。

在了解了pid namespace hierarchy之后，level成员也不难理解，任何一个系统分配的PID都是隶属于某一个namespace的，而这个namespace又是位于整个pid namespace hierarchy的某个层次上，pid->level指明了该PID所属的namespace的level。由于pid对其parent pid namespace也是可见的，因此，这个level值其实也就表示了这个pid对象在多少个pid namespace中可见。

在多少个pid namespace中可见，就会有多少个（pid namespace，pid number）对，numbers就是这样的一个数组，表示了在各个level上的pid number。tasks成员和使用该struct pid的task们关联，我们在下一节描述。

3、进程描述符中如何体现tid、pid、sid、pgid？

由于多个task共享ID（泛指上面说的四种ID），因此在设计数据结构的时候我们要考虑两种情况：

（1）从task struct快速找到对应的struct pid

（2）从struct pid能够遍历所有使用该pid的task

在这样的要求下，我们设计了一个辅助数据结构：

> struct pid\_link   
> {   
> struct hlist\_node node;   
> struct pid \*pid;   
> };

其中node是将task串接到struct pid的task struct链表中的节点，而pid指向具体的struct pid。这时候，我们可以在task struct中嵌入一个pid\_link的数组：

> struct task\_struct {   
> ……   
> struct pid\_link pids[PIDTYPE\_MAX];   
> ……   
> }

Task struct中的pids成员是一个数组，分别表示该task的tid（pid）、pgid和sid。我们定义pid的类型如下：

> enum pid\_type   
> {   
> PIDTYPE\_PID,   
> PIDTYPE\_PGID,   
> PIDTYPE\_SID,   
> PIDTYPE\_MAX   
> };

一直以来我们都是说四种type，tid、pid、sid、pgid，为何这里少定义一种呢？其实开始版本的内核的确是定义了四种type的pid，但是后来为了节省内存，tid和pid合二为一了。OK，现在已经引入太多的数据结构，下面我们用一幅图片来描述数据结构之间的关系：

[![pid-arch](/content/uploadfile/201702/d68660154f41b3235110853e0176b9a820170223111023.gif "pid-arch")](/content/uploadfile/201702/38ef0d410917067a562efbdaf834094c20170223111019.gif)

对于一个进程中的多个线程而言，每一个线程都可以通过task->pids[PIDTYPE\_PID].pid找到该线程对应的表示thread ID的那个struct pid数据对象。当然，任何一个线程都有其所属的进程，也就是有表示其process id的那个struct pid数据对象。如何找到它呢？这需要一个桥梁，也就是task struct中定义的thread group 成员（task->group\_leader），通过该指针，一个线程总是很容易的找到其对应的线程组leader，而线程组leader对应的pid就是该线程的process ID。因此，对于一个线程，其task->group\_leader->pids[PIDTYPE\_PID].pid就指向了表示其process id的那个struct pid数据对象。当然，对于线程组leader，其thread ID和process ID的struct pid数据对象是一个实体，对于非线程组leader的那些普通线程，其thread ID和process ID的struct pid数据对象指向不同的实体。

struct pid有三个链表头，如果该pid仅仅是标识一个thread ID，那么其pid链表头指向的链表中只有一个元素，就是使用该pid的task struct。如果该pid表示的是一个process ID，那么pid链表头指向的链表中多个task struct，每一个元素表示了属于该进程的线程的task struct，链表中第一个task struct是thread group leader。如果该pid并不表示一个process group ID或者session ID，那么struct pid中的pgid链表头和session链表头都是指向null。如果该pid表示一个process group ID的时候，其结构如下图所示：

[![pgid-arch](/content/uploadfile/201702/de6614bb9b99b259190103309d5c229d20170223111025.gif "pgid-arch")](/content/uploadfile/201702/5182e99ec9cd45d44cdb9aaa990e278520170223111024.gif)

对于那些multi-thread进程，内核有若干个task struct和进程对应，不过为了简单，在上面图片中，进程x 对应的task struct实际上是thread group leader对应的那个task struct。这些task struct的pgid指针（task->pids[PIDTYPE\_PGID].pid）指向了该进程组对应的struct pid数据对象。而该pid中的pgid链表头串联了所有使用该pid的task struct（仅仅是串联thread group leader对应的那些task struct），而链表中的第一个节点就是进程组leader。

session pid的概念是类似的，大家可以自行了解学习。

4、如何抽象 pid namespace？

好吧，这个有点复杂，暂时TODO吧。

五、代码分析

1、如何根据一个task struct得到其对应的thread ID？

> static inline struct pid \*task\_pid(struct task\_struct \*task)   
> {   
> return task->pids[PIDTYPE\_PID].pid;   
> }

同样的道理，我们也可以很容易得到一个task对应的pgid和sid。process ID有一点绕，我们首先要找到该task的thread group leader对应的task，其实一个线程的thread group leader对应的那个task的thread ID就是该线程的process ID。

2、如何根据一个task struct得到当前的pid namespace？

> struct pid\_namespace \*task\_active\_pid\_ns(struct task\_struct \*tsk)   
> {   
> return ns\_of\_pid(task\_pid(tsk));   
> }

这个操作可以分成两步，第一步首先找到其对应的thread ID，然后根据thread ID找到当前的pid namespace，代码如下：

> static inline struct pid\_namespace \*ns\_of\_pid(struct pid \*pid)   
> {   
> struct pid\_namespace \*ns = NULL;   
> if (pid)   
> ns = pid->numbers[pid->level].ns;   
> return ns;   
> }

一个struct pid实体是有层次的，对应了若干层次的（pid namespace，pid number）二元组，最顶层是root pid namespace，最底层（叶节点）是当前的pid namespace，pid->level表示了当前的层次，因此pid->numbers[pid->level].ns说明的就是当前的pid namespace。

3、getpid是如何实现的？

当陷入内核后，我们很容易获取当前的task struct（根据sp\_svc的值），这是起点，后续的代码如下：

> static inline pid\_t task\_tgid\_vnr(struct task\_struct \*tsk)   
> {   
> return pid\_vnr(task\_tgid(tsk));   
> }

通过task\_tgid可以获取该task对应的thread group leader的thread ID，其实也就是process ID。此外，通过task\_active\_pid\_ns亦可以获取当前的pid namespace，有了这两个参数，可以调用pid\_nr\_ns获取该task对应的pid number：

> pid\_t pid\_nr\_ns(struct pid \*pid, struct pid\_namespace \*ns)   
> {   
> struct upid \*upid;   
> pid\_t nr = 0;
>
> if (pid && ns->level <= pid->level) {   
> upid = &pid->numbers[ns->level];   
> if (upid->ns == ns)   
> nr = upid->nr;   
> }   
> return nr;   
> }

一个pid可以贯穿多个pid namespace，但是并非所有的pid namespace都可以检视pid，获取相应的pid number。因此，在代码的开始会进行验证，如果pid namespace的层次（ns->level）低于pid当前的pid namespace的层次，那么直接返回0。如果pid namespace的level是OK的，那么要检查该namespace是不是pid当前的那个pid namespace，如果是，直接返回对应的pid number，否则，返回0。

对于gettid和getppid这两个接口，整体的概念是和getpid类似的，不再赘述。

4、给定线程ID number的情况下，如何找对应的task struct？

这里给定的条件包括ID number、当前的pid namespace，在这样的条件下如何找到对应的task呢？我们分成两个步骤，第一个步骤是先找到对应的struct pid，代码如下：

> struct pid \*find\_pid\_ns(int nr, struct pid\_namespace \*ns)   
> {   
> struct upid \*pnr;
>
> hlist\_for\_each\_entry\_rcu(pnr,   
> &pid\_hash[pid\_hashfn(nr, ns)], pid\_chain)   
> if (pnr->nr == nr && pnr->ns == ns)   
> return container\_of(pnr, struct pid,   
> numbers[ns->level]);
>
> return NULL;   
> }

整个系统有那么多的struct pid数据对象，每一个pid又有多个level的（pid namespace，pid number）对，通过pid number和namespace来找对应的pid是一件非常耗时的操作。此外，这样的操作是一个比较频繁的操作，一个简单的例子就是通过kill向指定进程（pid number）发送信号。正是由于操作频繁而且耗时，系统建立了一个全局的哈希链表来解决这个问题，pid\_hash指向了若干（具体head的数量和内存配置有关）哈希链表头。这个哈希表用来通过一个指定pid namespace和id number，来找到对应的struct upid。一旦找了upid，那么通过container\_of找到对应的struct pid数据对象。

第二步是从struct pid找到task struct，代码如下：

> struct task\_struct \*pid\_task(struct pid \*pid, enum pid\_type type)   
> {   
> struct task\_struct \*result = NULL;   
> if (pid) {   
> struct hlist\_node \*first;   
> first = rcu\_dereference\_check(hlist\_first\_rcu(&pid->tasks[type]),   
> lockdep\_tasklist\_lock\_is\_held());   
> if (first)   
> result = hlist\_entry(first, struct task\_struct, pids[(type)].node);   
> }   
> return result;   
> }

5、getpgid是如何实现的？

> SYSCALL\_DEFINE1(getpgid, pid\_t, pid)   
> {   
> struct task\_struct \*p;   
> struct pid \*grp;   
> int retval;
>
> rcu\_read\_lock();   
> if (!pid)   
> grp = task\_pgrp(current);   
> else {   
> retval = -ESRCH;   
> p = find\_task\_by\_vpid(pid);   
> if (!p)   
> goto out;   
> grp = task\_pgrp(p);   
> if (!grp)   
> goto out;
>
> retval = security\_task\_getpgid(p);   
> if (retval)   
> goto out;   
> }   
> retval = pid\_vnr(grp);   
> out:   
> rcu\_read\_unlock();   
> return retval;   
> }

当传入的pid number等于0的时候，getpgid实际上是获取当前进程的process groud ID number，通过task\_pgrp可以获取该进程的使用的表示progress group ID对应的那个pid对象。如果调用getpgid的时候给出了非0的process ID number，那么getpgid实际上是想要获取指定pid number的gpid。这时候，我们需要调用find\_task\_by\_vpid找到该pid number对应的task struct。一旦找到task struct结构，那么很容易得到其使用的pgid（该实体是struct pid类型）。至此，无论哪一种参数情况（传入的参数pid number等于0或者非0），我们都找到了该pid number对应的struct pid数据对象（pgid）。当然，最终用户空间需要的是pgid number，因此我们需要调用pid\_vnr找到该pid在当前namespace中的pgid number。

getsid的代码逻辑和getpid是类似的，不再赘述。

*原创文章，转发请注明出处。蜗窝科技*
