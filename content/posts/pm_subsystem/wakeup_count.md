---
title: "Linux电源管理(8)_Wakeup count功能"
date: 2014-09-12T23:35:25+08:00
url: "/pm_subsystem/wakeup_count.html"
gid: "88"
emlog_type: "blog"
summary: "Wakeup count是 Wakeup events framework 的组成部分，用于解决“system suspend和system wakeup events之间的同步问题”。本文将结合“ Linux电源管理(6)_Generic PM之Suspend功能 ”和“ Linux电源管理(7)_Wakeup events framework ”两篇文章，分析wakeup count的功能、实"
author: "wowo"
category: "电源管理子系统"
category_alias: "pm_subsystem"
tags: ["Linux", "电源管理", "wakeup", "count"]
views: 56781
comment_count: 45
aliases:
  - "/pm_subsystem/88.html"
  - "/88.html"
---

#### 1. 前言

Wakeup count是[Wakeup events framework](/pm_subsystem/wakeup_events_framework.html)的组成部分，用于解决“system suspend和system wakeup events之间的同步问题”。本文将结合“[Linux电源管理(6)\_Generic PM之Suspend功能](/pm_subsystem/suspend_and_resume.html)”和“[Linux电源管理(7)\_Wakeup events framework](/pm_subsystem/wakeup_events_framework.html)”两篇文章，分析wakeup count的功能、实现逻辑、背后的思考，同时也是对这两篇文章的复习和总结。

#### 2. wakeup count在电源管理中的位置

wakeup count的实现位于wakeup events framework中（drivers/base/power/wakeup.c），主要为两个模块提供接口：通过PM core向用户空间提供sysfs接口；直接向autosleep（请参考下一篇文章）提供接口。

[![wakeup count architecture](/content/uploadfile/201409/61d89e824f195bc0c57ad29418fca54420140912153520.gif "wakeup count architecture")](/content/uploadfile/201409/7bd0e203b8ce640c3279d1a53b1994ab20140912153517.gif)

#### 3. wakeup count的功能

wakeup count的功能是suspend同步，实现思路是这样的：

1）任何想发起电源状态切换的实体（可以是用户空间电源管理进程，也可以是内核线程，简称C），在发起状态切换前，读取系统的wakeup counts（该值记录了当前的wakeup event总数），并将读取的counts告知wakeup events framework。

2）wakeup events framework记录该counts到一个全局变量中（saved\_count）。

3）随后C发起电源状态切换（如STR），执行suspend过程。

4）在suspend的过程中，wakeup events framework照旧工作（直到系统中断被关闭），上报wakeup events，增加wakeup events counts。

5）suspend执行的一些时间点（可参考“[Linux电源管理(6)\_Generic PM之Suspend功能](/pm_subsystem/suspend_and_resume.html)”），会调用wakeup events framework提供的接口（pm\_wakeup\_pending），检查是否有wakeup没有处理。

6）检查逻辑很简单，就是比较当前的wakeup counts和saved wakeup counts（C发起电源状态切换时的counts），如果不同，就要终止suspend过程。

#### 4. wakeup count的实现逻辑

##### 4.1 一个例子

在进行代码分析之前，我们先用伪代码的形式，写出一个利用wakeup count进行suspend操作的例子，然后基于该例子，分析相关的实现。

```
   1: do {
```

```
   2:     ret = read(&cnt, "/sys/power/wakeup_count");
```

```
   3:     if (ret) {
```

```
   4:         ret = write(cnt, "/sys/power/wakeup_count");
```

```
   5:     } else {
```

```
   6:         countine;
```

```
   7:     }
```

```
   8: } while (!ret);
```

```
   9:  
```

```
  10: write("mem", "/sys/power/state");
```

```
  11:  
```

```
  12: /* goto here after wakeup */
```

> 例子很简单：
>
> a）读取wakeup count值，如果成功，将读取的值回写。否则说明有正在处理的wakeup events，continue。
>
> b）回写后，判断返回值是否成功，如果不成功（说明读、写的过程中产生了wakeup events），继续读、写，直到成功。成功后，可以触发电源状态切换。

##### 4.2 /sys/power/wakeup\_count

wakeup\_count文件是在kernel/power/main.c中，利用power\_attr注册的，如下（大家可以仔细研读一下那一大段注释，内核很多注释写的非常好，而好的注释，就是软件功力的体现）：

```
   1: /*
```

```
   2:  * The 'wakeup_count' attribute, along with the functions defined in
```

```
   3:  * drivers/base/power/wakeup.c, provides a means by which wakeup events can be
```

```
   4:  * handled in a non-racy way.
```

```
   5:  *
```

```
   6:  * If a wakeup event occurs when the system is in a sleep state, it simply is
```

```
   7:  * woken up.  In turn, if an event that would wake the system up from a sleep
```

```
   8:  * state occurs when it is undergoing a transition to that sleep state, the
```

```
   9:  * transition should be aborted.  Moreover, if such an event occurs when the
```

```
  10:  * system is in the working state, an attempt to start a transition to the
```

```
  11:  * given sleep state should fail during certain period after the detection of
```

```
  12:  * the event.  Using the 'state' attribute alone is not sufficient to satisfy
```

```
  13:  * these requirements, because a wakeup event may occur exactly when 'state'
```

```
  14:  * is being written to and may be delivered to user space right before it is
```

```
  15:  * frozen, so the event will remain only partially processed until the system is
```

```
  16:  * woken up by another event.  In particular, it won't cause the transition to
```

```
  17:  * a sleep state to be aborted.
```

```
  18:  *
```

```
  19:  * This difficulty may be overcome if user space uses 'wakeup_count' before
```

```
  20:  * writing to 'state'.  It first should read from 'wakeup_count' and store
```

```
  21:  * the read value.  Then, after carrying out its own preparations for the system
```

```
  22:  * transition to a sleep state, it should write the stored value to
```

```
  23:  * 'wakeup_count'.  If that fails, at least one wakeup event has occurred since
```

```
  24:  * 'wakeup_count' was read and 'state' should not be written to.  Otherwise, it
```

```
  25:  * is allowed to write to 'state', but the transition will be aborted if there
```

```
  26:  * are any wakeup events detected after 'wakeup_count' was written to.
```

```
  27:  */
```

```
  28:  
```

```
  29: static ssize_t wakeup_count_show(struct kobject *kobj,
```

```
  30:                                 struct kobj_attribute *attr,
```

```
  31:                                 char *buf)
```

```
  32: {
```

```
  33:         unsigned int val;
```

```
  34:  
```

```
  35:         return pm_get_wakeup_count(&val, true) ?
```

```
  36:                 sprintf(buf, "%u\n", val) : -EINTR;
```

```
  37: }
```

```
  38:  
```

```
  39: static ssize_t wakeup_count_store(struct kobject *kobj,
```

```
  40:                                 struct kobj_attribute *attr,
```

```
  41:                                 const char *buf, size_t n)
```

```
  42: {
```

```
  43:         unsigned int val;
```

```
  44: int error;
```

```
  45:  
```

```
  46: error = pm_autosleep_lock();
```

```
  47: if (error)
```

```
  48:         return error;
```

```
  49:  
```

```
  50: if (pm_autosleep_state() > PM_SUSPEND_ON) {
```

```
  51:         error = -EBUSY;
```

```
  52:         goto out;
```

```
  53: }
```

```
  54:  
```

```
  55: error = -EINVAL;
```

```
  56: if (sscanf(buf, "%u", &val) == 1) {
```

```
  57:         if (pm_save_wakeup_count(val))
```

```
  58:                 error = n;
```

```
  59: }
```

```
  60:  
```

```
  61:  out:
```

```
  62: pm_autosleep_unlock();
```

```
  63: return error;
```

```
  64: }
```

```
  65:  
```

```
  66: tr(wakeup_count);
```

实现很简单：read时，直接调用pm\_get\_wakeup\_count（注意第2个参数）；write时，直接调用pm\_save\_wakeup\_count（注意用户空间的wakeup count功能和auto sleep互斥，会在下篇文章解释原因）。这两个接口均是wakeup events framework提供的接口，跟着代码往下看吧。

##### 4.3 pm\_get\_wakeup\_count

pm\_get\_wakeup\_count的实现如下：

```
   1: bool pm_get_wakeup_count(unsigned int *count, bool block)
```

```
   2: {
```

```
   3:         unsigned int cnt, inpr;
```

```
   4:  
```

```
   5:         if (block) {
```

```
   6:                 DEFINE_WAIT(wait);
```

```
   7:  
```

```
   8:                 for (;;) {
```

```
   9:                         prepare_to_wait(&wakeup_count_wait_queue, &wait,
```

```
  10:                                         TASK_INTERRUPTIBLE);
```

```
  11:                         split_counters(&cnt, &inpr);
```

```
  12:                         if (inpr == 0 || signal_pending(current))
```

```
  13:                                 break;
```

```
  14:  
```

```
  15:                         schedule();
```

```
  16:                 }
```

```
  17:                 finish_wait(&wakeup_count_wait_queue, &wait);
```

```
  18:         }
```

```
  19:  
```

```
  20:         split_counters(&cnt, &inpr);
```

```
  21:         *count = cnt;
```

```
  22:         return !inpr;
```

```
  23: }
```

> 该接口有两个参数，一个是保存返回的count值得指针，另一个指示是否block，具体请参考代码逻辑：
>
> a）如果block为false，直接读取registered wakeup events和wakeup events in progress两个counter值，将registered wakeup events交给第一个参数，并返回wakeup events in progress的状态（若返回false，说明当前有wakeup events正在处理，不适合suspend）。
>
> b）如果block为true，定义一个等待队列，等待wakeup events in progress为0，再返回counter。
>
> 注1：由4.2小节可知，sysfs发起的read动作，block为true，所以如果有正在处理的wakeup events，read进程会阻塞。其它模块（如auto sleep）发起的read，则可能不需要阻塞。

##### 4.4 pm\_save\_wakeup\_count

pm\_save\_wakeup\_count的实现如下：

```
   1: bool pm_save_wakeup_count(unsigned int count)
```

```
   2: {
```

```
   3:         unsigned int cnt, inpr;
```

```
   4:         unsigned long flags;
```

```
   5:  
```

```
   6:         events_check_enabled = false;
```

```
   7:         spin_lock_irqsave(&events_lock, flags);
```

```
   8:         split_counters(&cnt, &inpr);
```

```
   9:         if (cnt == count && inpr == 0) {
```

```
  10:                 saved_count = count;
```

```
  11:                 events_check_enabled = true;
```

```
  12:         }
```

```
  13:         spin_unlock_irqrestore(&events_lock, flags);
```

```
  14:         return events_check_enabled;
```

```
  15: }
```

> 1）注意这个变量，events\_check\_enabled，如果它不为真，pm\_wakeup\_pending接口直接返回false，意味着如果不利用wakeup count功能，suspend过程中不会做任何wakeup events检查，也就不会进行任何的同步。
>
> 2）解除当前的registered wakeup events、wakeup events in progress，保存在变量cnt和inpr中。
>
> 3）如果写入的值和cnt不同（说明读、写的过程中产生events），或者inpr不为零（说明有events正在被处理），返回false（说明此时不宜suspend）。
>
> 4）否则，events\_check\_enabled置位（后续的pm\_wakeup\_pending才会干活），返回true（可以suspend），并将当前的wakeup count保存在saved count变量中。

##### 4.5 /sys/power/state

再回忆一下“[Linux电源管理(6)\_Generic PM之Suspend功能](/pm_subsystem/suspend_and_resume.html)”中suspend的流程，在suspend\_enter接口中，suspend前的最后一刻，会调用pm\_wakeup\_pending接口，代码如下：

```
   1: static int suspend_enter(suspend_state_t state, bool *wakeup)
```

```
   2: {
```

```
   3:     ...
```

```
   4:     error = syscore_suspend();
```

```
   5:     if (!error) {
```

```
   6:         *wakeup = pm_wakeup_pending();
```

```
   7:         if (!(suspend_test(TEST_CORE) || *wakeup)) {
```

```
   8:                 error = suspend_ops->enter(state);
```

```
   9:                 events_check_enabled = false;
```

```
  10:         }
```

```
  11:         syscore_resume();
```

```
  12:     }
```

```
  13:     ...
```

```
  14: }
```

在write wakeup\_count到调用pm\_wakeup\_pending这一段时间内，wakeup events framework会照常产生wakeup events，因此如果pending返回true，则不能“enter”，终止suspend吧！

注2：wakeup后，会清除events\_check\_enabled标记。

“[Linux电源管理(7)\_Wakeup events framework](/pm_subsystem/wakeup_events_framework.html)”中已经介绍过pm\_wakeup\_pending了，让我们再看一遍吧：

```
   1: bool pm_wakeup_pending(void)
```

```
   2: {
```

```
   3:         unsigned long flags;
```

```
   4:         bool ret = false;
```

```
   5:  
```

```
   6:         spin_lock_irqsave(&events_lock, flags);
```

```
   7:         if (events_check_enabled) {
```

```
   8:                 unsigned int cnt, inpr;
```

```
   9:  
```

```
  10:                 split_counters(&cnt, &inpr);
```

```
  11:                 ret = (cnt != saved_count || inpr > 0);
```

```
  12:                 events_check_enabled = !ret;
```

```
  13:         }
```

```
  14:         spin_unlock_irqrestore(&events_lock, flags);
```

```
  15:  
```

```
  16:         if (ret)
```

```
  17:                 print_active_wakeup_sources();
```

```
  18:  
```

```
  19:         return ret;
```

```
  20: }
```

> a）首先会判断events\_check\_enabled是否有效，无效直接返回false。有效的话：
>
> b）获得cnt和inpr，如果cnt不等于saved\_count（说明这段时间内有events产生），或者inpr不为0（说明有events正在被处理），返回true（告诉调用者，放弃吧，时机不到）。同时清除events\_check\_enabled的状态。
>
> c）否则，返回false（放心睡吧），同时保持events\_check\_enabled的置位状态（以免pm\_wakeup\_pending再次调用）。

Okay，结束了，等待wakeup吧~~~~

*原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/pm_subsystem/wakeup_count.html)。*
