---
title: "Linux vm运行参数之（二）：OOM相关的参数"
date: 2015-09-28T12:10:53+08:00
url: "/memory_management/oom.html"
gid: "213"
emlog_type: "blog"
summary: "本文是描述Linux virtual memory运行参数的第二篇，主要是讲OOM相关的参数的。为了理解OOM参数，第二章简单的描述什么是OOM。如果这个名词对你毫无压力，你可以直接 进入第三章，这一章是描述具体的参数的，除了描述具体的参数，我们引用了一些具体的内核代码，本文的代码来自4.0内核，如果有兴趣，可以结合代码阅读， 为了缩减篇幅，文章中的代码都是删减版本的。按照惯例，最后一章是参考文献"
author: "linuxer"
category: "内存管理"
category_alias: "memory_management"
tags: ["oom"]
views: 42667
comment_count: 20
aliases:
  - "/memory_management/213.html"
  - "/213.html"
---

一、前言

本文是描述Linux virtual memory运行参数的第二篇，主要是讲OOM相关的参数的。为了理解OOM参数，第二章简单的描述什么是OOM。如果这个名词对你毫无压力，你可以直接进入第三章，这一章是描述具体的参数的，除了描述具体的参数，我们引用了一些具体的内核代码，本文的代码来自4.0内核，如果有兴趣，可以结合代码阅读，为了缩减篇幅，文章中的代码都是删减版本的。按照惯例，最后一章是参考文献，本文的参考文献都是来自linux内核的Documentation目录，该目录下有大量的文档可以参考，每一篇都值得细细品味。

二、什么是OOM

OOM就是out of memory的缩写，虽然linux kernel有很多的内存管理技巧（从cache中回收、swap out等）来满足各种应用空间的vm内存需求，但是，当你的系统配置不合理，让一匹小马拉大车的时候，linux kernel会运行非常缓慢并且在某个时间点分配page frame的时候遇到内存耗尽、无法分配的状况。应对这种状况首先应该是系统管理员，他需要首先给系统增加内存，不过对于kernel而言，当面对OOM的时候，咱们也不能慌乱，要根据OOM参数来进行相应的处理。

三、OOM参数

1、panic\_on\_oom

当kernel遇到OOM的时候，可以有两种选择：

（1）产生kernel panic（就是死给你看）。

（2）积极面对人生，选择一个或者几个最“适合”的进程，启动OOM killer，干掉那些选中的进程，释放内存，让系统勇敢的活下去。

panic\_on\_oom这个参数就是控制遇到OOM的时候，系统如何反应的。当该参数等于0的时候，表示选择积极面对人生，启动OOM killer。当该参数等于2的时候，表示无论是哪一种情况，都强制进入kernel panic。panic\_on\_oom等于其他值的时候，表示要区分具体的情况，对于某些情况可以panic，有些情况启动OOM killer。kernel的代码中，enum oom\_constraint 就是一个进一步描述OOM状态的参数。系统遇到OOM总是有各种各样的情况的，kernel中定义如下：

> enum oom\_constraint {   
> CONSTRAINT\_NONE,   
> CONSTRAINT\_CPUSET,   
> CONSTRAINT\_MEMORY\_POLICY,   
> CONSTRAINT\_MEMCG,   
> };

对于UMA而言， oom\_constraint永远都是CONSTRAINT\_NONE，表示系统并没有什么约束就出现了OOM，不要想太多了，就是内存不足了。在NUMA的情况下，有可能附加了其他的约束导致了系统遇到OOM状态，实际上，系统中还有充足的内存。这些约束包括：

（1）CONSTRAINT\_CPUSET。cpusets是kernel中的一种机制，通过该机制可以把一组cpu和memory node资源分配给特定的一组进程。这时候，如果出现OOM，仅仅说明该进程能分配memory的那个node出现状况了，整个系统有很多的memory node，其他的node可能有充足的memory资源。

（2）CONSTRAINT\_MEMORY\_POLICY。memory policy是NUMA系统中如何控制分配各个memory node资源的策略模块。用户空间程序（NUMA-aware的程序）可以通过memory policy的API，针对整个系统、针对一个特定的进程，针对一个特定进程的特定的VMA来制定策略。产生了OOM也有可能是因为附加了memory policy的约束导致的，在这种情况下，如果导致整个系统panic似乎有点不太合适吧。

（3）CONSTRAINT\_MEMCG。MEMCG就是memory control group，Cgroup这东西太复杂，这里不适合多说，Cgroup中的memory子系统就是控制系统memory资源分配的控制器，通俗的将就是把一组进程的内存使用限定在一个范围内。当这一组的内存使用超过上限就会OOM，在这种情况下的OOM就是CONSTRAINT\_MEMCG类型的OOM。

OK，了解基础知识后，我们来看看内核代码。内核中sysctl\_panic\_on\_oom变量是和/proc/sys/vm/panic\_on\_oom对应的，主要的判断逻辑如下：

> void check\_panic\_on\_oom(enum oom\_constraint constraint, gfp\_t gfp\_mask,   
> int order, const nodemask\_t \*nodemask)   
> {   
> if (likely(!sysctl\_panic\_on\_oom))－－－－0表示启动OOM killer，因此直接return了   
> return;   
> if (sysctl\_panic\_on\_oom != 2) {－－－－2是强制panic，不是2的话，还可以商量   
> if (constraint != CONSTRAINT\_NONE)－－－在有cpuset、memory policy、memcg的约束情况下   
> return; 的OOM，可以考虑不panic，而是启动OOM killer   
> }   
> dump\_header(NULL, gfp\_mask, order, NULL, nodemask);   
> panic("Out of memory: %s panic\_on\_oom is enabled\n",   
> sysctl\_panic\_on\_oom == 2 ? "compulsory" : "system-wide");－－－死给你看啦   
> }

2、oom\_kill\_allocating\_task

当系统选择了启动OOM killer，试图杀死某些进程的时候，又会遇到这样的问题：干掉哪个，哪一个才是“合适”的哪那个进程？系统可以有下面的选择：

（1）谁触发了OOM就干掉谁

（2）谁最“坏”就干掉谁

oom\_kill\_allocating\_task这个参数就是控制这个选择路径的，当该参数等于0的时候选择（2），否则选择（1）。具体的代码可以在参考\_\_out\_of\_memory函数，具体如下：

> static void \_\_out\_of\_memory(struct zonelist \*zonelist, gfp\_t gfp\_mask,   
> int order, nodemask\_t \*nodemask, bool force\_kill) {
>
> ……   
> check\_panic\_on\_oom(constraint, gfp\_mask, order, mpol\_mask);
>
> if (sysctl\_oom\_kill\_allocating\_task && current->mm &&   
> !oom\_unkillable\_task(current, NULL, nodemask) &&   
> current->signal->oom\_score\_adj != OOM\_SCORE\_ADJ\_MIN) {   
> get\_task\_struct(current);   
> oom\_kill\_process(current, gfp\_mask, order, 0, totalpages, NULL,   
> nodemask, "Out of memory (oom\_kill\_allocating\_task)");   
> goto out;   
> }
>
> ……   
> }

当然也不能说杀就杀，还是要考虑是否用户空间进程（不能杀内核线程）、是否unkillable task（例如init进程就不能杀），用户空间是否通过设定参数（oom\_score\_adj）阻止kill该task。如果万事俱备，那么就调用oom\_kill\_process干掉当前进程。

3、oom\_dump\_tasks

当系统的内存出现OOM状况，无论是panic还是启动OOM killer，做为系统管理员，你都是想保留下线索，找到OOM的root cause，例如dump系统中所有的用户空间进程关于内存方面的一些信息，包括：进程标识信息、该进程使用的total virtual memory信息、该进程实际使用物理内存（我们又称之为RSS，Resident Set Size，不仅仅是自己程序使用的物理内存，也包含共享库占用的内存），该进程的页表信息等等。拿到这些信息后，有助于了解现象（出现OOM）之后的真相。

当设定为0的时候，上一段描述的各种进程们的内存信息都不会打印出来。在大型的系统中，有几千个进程，逐一打印每一个task的内存信息有可能会导致性能问题（要知道当时已经是OOM了）。当设定为非0值的时候，在下面三种情况会调用dump\_tasks来打印系统中所有task的内存状况：

（1）由于OOM导致kernel panic

（2）没有找到适合的“bad”process

（3）找适合的并将其干掉的时候

4、oom\_adj、oom\_score\_adj和oom\_score

准确的说这几个参数都是和具体进程相关的，因此它们位于/proc/xxx/目录下（xxx是进程ID）。假设我们选择在出现OOM状况的时候杀死进程，那么一个很自然的问题就浮现出来：到底干掉哪一个呢？内核的算法倒是非常简单，那就是打分（oom\_score，注意，该参数是read only的），找到分数最高的就OK了。那么怎么来算分数呢？可以参考内核中的oom\_badness函数：

> unsigned long oom\_badness(struct task\_struct \*p, struct mem\_cgroup \*memcg,   
> const nodemask\_t \*nodemask, unsigned long totalpages)   
> {……
>
> adj = (long)p->signal->oom\_score\_adj;   
> if (adj == OOM\_SCORE\_ADJ\_MIN) {－－－－－－－－－－－－－－－－－－－－－－（1）   
> task\_unlock(p);   
> return 0;－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－（2）   
> }
>
> points = get\_mm\_rss(p->mm) + get\_mm\_counter(p->mm, MM\_SWAPENTS) +   
> atomic\_long\_read(&p->mm->nr\_ptes) + mm\_nr\_pmds(p->mm);－－－－－－－－－（3）   
> task\_unlock(p);
>
> if (has\_capability\_noaudit(p, CAP\_SYS\_ADMIN))－－－－－－－－－－－－－－－－－（4）   
> points -= (points \* 3) / 100;
>
> adj \*= totalpages / 1000;－－－－－－－－－－－－－－－－－－－－－－－－－－－－（5）   
> points += adj;   
>   
> return points > 0 ? points : 1;   
> }

（1）对某一个task进行打分（oom\_score）主要有两部分组成，一部分是系统打分，主要是根据该task的内存使用情况。另外一部分是用户打分，也就是oom\_score\_adj了，该task的实际得分需要综合考虑两方面的打分。如果用户将该task的 oom\_score\_adj设定成OOM\_SCORE\_ADJ\_MIN（-1000）的话，那么实际上就是禁止了OOM killer杀死该进程。

（2）这里返回了0也就是告知OOM killer，该进程是“good process”，不要干掉它。后面我们可以看到，实际计算分数的时候最低分是1分。

（3）前面说过了，系统打分就是看物理内存消耗量，主要是三部分，RSS部分，swap file或者swap device上占用的内存情况以及页表占用的内存情况。

（4）root进程有3%的内存使用特权，因此这里要减去那些内存使用量。

（5）用户可以调整oom\_score，具体如何操作呢？oom\_score\_adj的取值范围是-1000～1000，0表示用户不调整oom\_score，负值表示要在实际打分值上减去一个折扣，正值表示要惩罚该task，也就是增加该进程的oom\_score。在实际操作中，需要根据本次内存分配时候可分配内存来计算（如果没有内存分配约束，那么就是系统中的所有可用内存，如果系统支持cpuset，那么这里的可分配内存就是该cpuset的实际额度值）。oom\_badness函数有一个传入参数totalpages，该参数就是当时的可分配的内存上限值。实际的分数值（points）要根据oom\_score\_adj进行调整，例如如果oom\_score\_adj设定-500，那么表示实际分数要打五折（基数是totalpages），也就是说该任务实际使用的内存要减去可分配的内存上限值的一半。

了解了oom\_score\_adj和oom\_score之后，应该是尘埃落定了，oom\_adj是一个旧的接口参数，其功能类似oom\_score\_adj，为了兼容，目前仍然保留这个参数，当操作这个参数的时候，kernel实际上是会换算成oom\_score\_adj，有兴趣的同学可以自行了解，这里不再细述了。

四、参考文献

1、Documentation/vm/numa\_memory\_policy.txt

2、Documentation/sysctl/vm.txt

3、Documentation/cgroup/cpusets.txt

4、Documentation/cgroup/memory.txt

5、Documentation/filesystems/proc.txt

*原创文章，转发请注明出处。蜗窝科技*
