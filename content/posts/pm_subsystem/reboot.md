---
title: "Linux电源管理(3)_Generic PM之Reboot过程"
date: 2014-05-19T15:44:43+08:00
url: "/pm_subsystem/reboot.html"
gid: "43"
emlog_type: "blog"
summary: "\r\n\t在使用计算机的过程中，关机和重启是最先学会的两个操作。同样，这两个操作在Linux中也存在，称作shutdown和restart。这就是本文要描述的对象。\r\n\r\n\r\n\t在Linux Kernel中，主流的shutdown和restart都是通过“reboot”系统调用（具体可参考kernel/sys.c）来实现的，这也是本文使用“Generic PM之Reboot过程”作为标题的原因。另外，"
author: "wowo"
category: "电源管理子系统"
category_alias: "pm_subsystem"
tags: ["Linux", "PM", "电源管理", "reboot", "power_off"]
views: 83863
comment_count: 37
aliases:
  - "/pm_subsystem/43.html"
  - "/43.html"
---

#### 1. 前言

在使用计算机的过程中，关机和重启是最先学会的两个操作。同样，这两个操作在Linux中也存在，称作shutdown和restart。这就是本文要描述的对象。

在Linux Kernel中，主流的shutdown和restart都是通过“reboot”系统调用（具体可参考kernel/sys.c）来实现的，这也是本文使用“Generic PM之Reboot过程”作为标题的原因。另外，除了我们常用的shutdown和restart两类操作之外，该系统调用也提供了其它的reboot方式，也会在这里一一说明。

#### 2. Kernel支持的reboot方式

也许你会奇怪，reboot是重启的意思，所以用它实现Restart是合理的，但怎么用它实现关机操作呢？答案是这样的：关机之后，早晚也会开机啊！所以关机是一种特殊的Restart过程，只不过持续的时间有点长而已。所以，内核根据不同的表现方式，将reboot分为如下的几种方式：

```
   1: /*      
```

```
   2:  * Commands accepted by the _reboot() system call.
```

```
   3:  *
```

```
   4:  * RESTART     Restart system using default command and mode.
```

```
   5:  * HALT        Stop OS and give system control to ROM monitor, if any.
```

```
   6:  * CAD_ON      Ctrl-Alt-Del sequence causes RESTART command.
```

```
   7:  * CAD_OFF     Ctrl-Alt-Del sequence sends SIGINT to init task.
```

```
   8:  * POWER_OFF   Stop OS and remove all power from system, if possible.
```

```
   9:  * RESTART2    Restart system using given command string.
```

```
  10:  * SW_SUSPEND  Suspend system using software suspend if compiled in.
```

```
  11:  * KEXEC       Restart system using a previously loaded Linux kernel
```

```
  12:  */
```

```
  13:         
```

```
  14: #define LINUX_REBOOT_CMD_RESTART        0x01234567
```

```
  15: #define LINUX_REBOOT_CMD_HALT           0xCDEF0123
```

```
  16: #define LINUX_REBOOT_CMD_CAD_ON         0x89ABCDEF
```

```
  17: #define LINUX_REBOOT_CMD_CAD_OFF        0x00000000
```

```
  18: #define LINUX_REBOOT_CMD_POWER_OFF      0x4321FEDC
```

```
  19: #define LINUX_REBOOT_CMD_RESTART2       0xA1B2C3D4
```

```
  20: #define LINUX_REBOOT_CMD_SW_SUSPEND     0xD000FCE2
```

```
  21: #define LINUX_REBOOT_CMD_KEXEC          0x4558454
```

> RESTART，正常的重启，也是我们平时使用的重启。执行该动作后，系统会重新启动。
>
> HALT，停止操作系统，然后把控制权交给其它代码（如果有的话）。具体的表现形式，依赖于系统的具体实现。
>
> CAD\_ON/CAD\_OFF，允许/禁止通过Ctrl-Alt-Del组合按键触发重启（RESTART）动作。
>   
> 注1：Ctrl-Alt-Del组合按键的响应是由具体的Driver（如Keypad）实现的。
>
> POWER\_OFF，正常的关机。执行该动作后，系统会停止操作系统，并去除所有的供电。
>
> RESTART2，重启的另一种方式。可以在重启时，携带一个字符串类型的cmd，该cmd会在重启前，发送给任意一个关心重启事件的进程，同时会传递给最终执行重启动作的machine相关的代码。内核并没有规定该cmd的形式，完全由具体的machine自行定义。
>
> SW\_SUSPEND，即前一篇文章中描述的Hibernate操作，会在下一篇文章描述，这里就暂不涉及。
>
> KEXEC，重启并执行已经加载好的其它Kernel Image（需要CONFIG\_KEXEC的支持），暂不涉及。

#### 3. Reboot相关的操作流程

在Linux操作系统中，可以通过reboot、halt、poweroff等命令，发起reboot，具体的操作流程如下：

[![Reboot相关的操作流程](/content/uploadfile/201405/099c6373be7ab3002cd0aeaf2260ae2520140519074443.gif "Reboot相关的操作流程")](/content/uploadfile/201405/1967cf3baa13596e902e2a779e47405620140519074441.gif)

- 一般的Linux操作系统，在用户空间都提供了一些工具集合（如常在嵌入式系统使用的Busybox），这些工具集合包含了reboot、halt和poweroff三个和Reboot相关的命令。读者可以参考man帮助文档，了解这些命令的解释和使用说明
- 用户空间程序通过reboot系统调用，进入内核空间
- 内核空间根据执行路径的不同，提供了kernel\_restart、kernel\_halt和kernel\_power\_off三个处理函数，响应用空间的reboot请求
- 这三个处理函数的处理流程大致相同，主要包括：向关心reboot过程的进程发送Notify事件；调用drivers核心模块提供的接口，关闭所有的外部设备；调用drivers syscore模块提供的接口，关闭system core；调用Architecture相关的处理函数，进行后续的处理；最后，调用machine相关的接口，实现真正意义上的Reboot
- 另外，借助TTY模块提供的Sysreq机制，内核提供了其它途径的关机方法，如某些按键组合、向/proc文件写入命令等，后面会详细介绍

#### 4. Reboot过程的内部动作和代码分析

##### 4.1 Reboot系统调用

Reboot系统调用的实现位于“kernel/sys.c”，其函数原型如下：

```
   1: SYSCALL_DEFINE4(reboot, int, magic1, int, magic2, unsigned int, cmd,
```

```
   2:                 void __user *, arg)
```

该函数的参数解释如下：

> reboot，该系统调用的名称。
>
> magic1、magic2，两个int类型的“魔力数”，用于防止误操作。具体在“include/uapi/linux/reboot.h”中定义，感兴趣的同学可以去看看（话说这些数字还是蛮有意思的，例如Linus同学及其家人的生日就在里面，猜出来的可以在文章下面留言）。
>
> cmd，第2章所讲述的reboot方式。
>
> arg，其它的额外参数。

reboot系统调用的内部动作比较简单：

> 1）判断调用者的用户权限，如果不是超级用户（superuser），则直接返回错误（这也是我们再用户空间执行reboot、halt、poweroff等命令时，必须是root用户的原因）；
>
> 2）判断传入的magic number是否匹配，如果不匹配，直接返回错误。这样就可以尽可能的防止误动作发生；
>
> 3）调用reboot\_pid\_ns接口，检查是否需要由该接口处理reboot请求。这是一个有关pid namespaces的新特性，也是Linux内核重要的知识点，我们会在其它文章中描述，这里就不多说了；
>
> 4）如果是POWER\_OFF命令，且没有注册power off的machine处理函数（pm\_power\_off），把该命令转换为HALT命令；
>
> 5）根据具体的cmd命令，执行具体的处理，包括，
>   
>  如果是RESTART或者RESTART2命令，调用kernel\_restart。
>   
>  如果是CAD\_ON或CAD\_OFF命令，更新C\_A\_D的值，表示是否允许通过Ctrl+Alt+Del组合键重启系统。
>   
>  如果是HALT命令，调用kernel\_halt。
>   
>  如果是POWER\_OFF命令，调用kernel\_power\_off。
>   
>  如果是KEXEC命令，调用kernel\_kexec接口（暂不在本文涉及）。
>   
>  如果是SW\_SUSPEND，调用hibernate接口（会在下一章描述）；
>
> 6）返回上述的处理结果，系统调用结束。

##### 4.2 kernel\_restart、kernel\_halt和kernel\_power\_off

这三个接口也位于“kernel/sys.c”，实现比较类似，具体动作包括：

> 1）调用kernel\_xxx\_prepare函数，进行restart/halt/power\_off前的准备工作，包括，
>   
>  调用blocking\_notifier\_call\_chain接口，向关心reboot事件的进程，发送SYS\_RESTART、SYS\_HALT或者SYS\_POWER\_OFF事件。对RESTART来说，还好将cmd参数一并发送出去。
>   
>  将系统状态设置为相应的状态（SYS\_RESTART、SYS\_HALT或SYS\_POWER\_OFF）。
>   
>  调用usermodehelper\_disable接口，禁止User mode helper（可参考“[Linux设备模型(3)\_Uevent](/device_model/uevent.html)”相关的描述）。
>   
>  调用device\_shutdown，关闭所有的设备（具体内容会在下一节讲述）；
>
> 2）如果是power\_off，且存在PM相关的power off prepare函数（pm\_power\_off\_prepare），则调用该回调函数；
>
> 3）调用migrate\_to\_reboot\_cpu接口，将当前的进程（task）移到一个CPU上；
>   
> 注2：对于多CPU的机器，无论哪个CPU触发了当前的系统调用，代码都可以运行在任意的CPU上。这个接口将代码分派到一个特定的CPU上，并禁止调度器分派代码到其它CPU上。也就是说，这个接口被执行后，只有一个CPU在运行，用于完成后续的reboot动作。
>
> 4）调用syscore\_shutdown接口，将系统核心器件关闭（例如中断等）；
>
> 5）调用printk以及kmsg\_dump，向这个世界发出最后的声音（打印日志）；
>
> 6）最后，由machine-core的代码，接管后续的处理。

##### 4.3 device\_shutdown

在理解device\_shutdown之前，我们需要回忆一下前几篇有关[Linux设备模型](/tag/%E8%AE%BE%E5%A4%87%E6%A8%A1%E5%9E%8B)的文章。同时，借助对电源管理的解析，我们会把在[Linux设备模型](/tag/%E8%AE%BE%E5%A4%87%E6%A8%A1%E5%9E%8B)系列文章中没有描述的部分补回来。设备模型中和device\_shutdown有关的逻辑包括：

- 每个设备（struct device）都会保存该设备的驱动（struct device\_driver）指针，以及该设备所在总线（struct bus\_type）的指针（具体参考“[Linux设备模型(5)\_device和device driver](/device_model/device_and_driver.html)”）
- 设备驱动中有一个名称为“shutdown”的回调函数，用于在device\_shutdown时，关闭该设备（具体参考“[Linux设备模型(5)\_device和device driver](/device_model/device_and_driver.html)”）
- 总线中也有一个名称为“shutdown”的回调函数，用于在device\_shutdown时，关闭该设备（具体参考“[Linux设备模型(6)\_Bus](/device_model/bus.html)”）
- 系统的所有设备，都存在于“/sys/devices/”目录下，而该目录由名称为“devices\_kset”的kset表示。而由“[Linux设备模型(2)\_Kobject](/device_model/kobject.html)”的描述可知，kset中会使用一个链表保存其下所有的kobject（也即“/sys/devices/”目录下的所有设备）。最终的结果就是，以“devices\_kset”为root节点，将内核中所有的设备（以相应的kobject为代表），组织成一个树状结构

介绍完以上的背景知识，我们来看device\_shutdown的实现，就非常容易了。该接口位于“drivers/base/core.c”中，执行逻辑如下。

```
   1: /**
```

```
   2:  * device_shutdown - call ->shutdown() on each device to shutdown.
```

```
   3:  */
```

```
   4: void device_shutdown(void)
```

```
   5: {
```

```
   6:         struct device *dev, *parent;
```

```
   7:         
```

```
   8:         spin_lock(&devices_kset->list_lock);
```

```
   9:         /*
```

```
  10:          * Walk the devices list backward, shutting down each in turn.
```

```
  11:          * Beware that device unplug events may also start pulling
```

```
  12:          * devices offline, even as the system is shutting down.
```

```
  13:          */
```

```
  14:         while (!list_empty(&devices_kset->list)) {
```

```
  15:                 dev = list_entry(devices_kset->list.prev, struct device,
```

```
  16:                                 kobj.entry);
```

```
  17:  
```

```
  18:                 /*
```

```
  19:                  * hold reference count of device's parent to
```

```
  20:                  * prevent it from being freed because parent's
```

```
  21:                  * lock is to be held
```

```
  22:                  */
```

```
  23:                 parent = get_device(dev->parent);
```

```
  24:                 get_device(dev);
```

```
  25:                 /*
```

```
  26:                  * Make sure the device is off the kset list, in the
```

```
  27:                  * event that dev->*->shutdown() doesn't remove it.
```

```
  28:                  */
```

```
  29:                 list_del_init(&dev->kobj.entry);
```

```
  30:                 spin_unlock(&devices_kset->list_lock);
```

```
  31:  
```

```
  32:                 /* hold lock to avoid race with probe/release */
```

```
  33:                 if (parent)
```

```
  34:                         device_lock(parent);
```

```
  35:                 device_lock(dev);
```

```
  36:  
```

```
  37:                 /* Don't allow any more runtime suspends */
```

```
  38:                 pm_runtime_get_noresume(dev);
```

```
  39:                 pm_runtime_barrier(dev);
```

```
  40:  
```

```
  41:                 if (dev->bus && dev->bus->shutdown) {
```

```
  42:                         if (initcall_debug)
```

```
  43:                                 dev_info(dev, "shutdown\n");
```

```
  44:                         dev->bus->shutdown(dev);
```

```
  45:                 } else if (dev->driver && dev->driver->shutdown) {
```

```
  46:                         if (initcall_debug)
```

```
  47:                                 dev_info(dev, "shutdown\n");
```

```
  48:                         dev->driver->shutdown(dev);
```

```
  49:                 }
```

```
  50:  
```

```
  51:                 device_unlock(dev);
```

```
  52:                 if (parent)
```

```
  53:                         device_unlock(parent);
```

```
  54:  
```

```
  55:                 put_device(dev);
```

```
  56:                 put_device(parent);
```

```
  57:  
```

```
  58:                 spin_lock(&devices_kset->list_lock);
```

```
  59:         }
```

```
  60:         spin_unlock(&devices_kset->list_lock);
```

```
  61:         async_synchronize_full();
```

```
  62: }
```

> 1）遍历devices\_kset的链表，取出所有的设备（struct device）；
>
> 2）将该设备从链表中删除；
>
> 3）调用pm\_runtime\_get\_noresume和pm\_runtime\_barrier接口，停止所有的Runtime相关的电源管理动作（后续的文章会详细描述有关Runtime PM的逻辑）；
>
> 4）如果该设备的bus提供了shutdown函数，优先调用bus的shutdown，关闭设备；
>
> 5）如果bus没有提供shutdown函数，检测设备driver是否提供，如果提供，调用设备driver的shutdown，关闭设备；
>
> 6）直至处理完毕所有的设备。

##### 4.4 system\_core\_shutdown

system core的shutdown和设备的shutdown类似，也是从一个链表中，遍历所有的system core，并调用它的shutdown接口。后续蜗蜗会专门写一篇文章介绍syscore，这里暂不描述。

##### 4.5 machine\_restart、machine\_halt和machine\_power\_off

虽然以machine\_为前缀命名，这三个接口却是属于Architecture相关的处理函数，如ARM。以ARM为例，它们在“arch/arm/kernel/process.c”中实现，具体如下。

###### 4.5.1 machine\_restart

```
   1: /*
```

```
   2:  * Restart requires that the secondary CPUs stop performing any activity
```

```
   3:  * while the primary CPU resets the system. Systems with a single CPU can
```

```
   4:  * use soft_restart() as their machine descriptor's .restart hook, since that
```

```
   5:  * will cause the only available CPU to reset. Systems with multiple CPUs must
```

```
   6:  * provide a HW restart implementation, to ensure that all CPUs reset at once.
```

```
   7:  * This is required so that any code running after reset on the primary CPU
```

```
   8:  * doesn't have to co-ordinate with other CPUs to ensure they aren't still
```

```
   9:  * executing pre-reset code, and using RAM that the primary CPU's code wishes
```

```
  10:  * to use. Implementing such co-ordination would be essentially impossible.
```

```
  11:  */
```

```
  12: void machine_restart(char *cmd)
```

```
  13: {
```

```
  14:         smp_send_stop();
```

```
  15:  
```

```
  16:         arm_pm_restart(reboot_mode, cmd);
```

```
  17:  
```

```
  18:         /* Give a grace period for failure to restart of 1s */
```

```
  19:         mdelay(1000);
```

```
  20:  
```

```
  21:         /* Whoops - the platform was unable to reboot. Tell the user! */
```

```
  22:         printk("Reboot failed -- System halted\n");
```

```
  23:         local_irq_disable();
```

```
  24:         while (1);
```

```
  25: }
```

> 0）先转述一下该接口的注释；
>   
> 对于多CPU的机器来说，Restart之前必须保证其它的CPU处于非活动状态，由其中的一个主CPU负责Restart动作。并且，必须实现一个基于硬件的Restart操作，以保证所有CPU同步Restart，这是设计的重点！
>   
> 对于单CPU机器来说，就相对简单了，可以直接用软件reset的方式实现Restart。
>
> 1）调用smp\_send\_stop接口，确保其它CPU处于非活动状态；
>
> 2）调用machine-dependent的restart接口，实现真正的restart。该接口是一个回调函数，由“arch/arm/kernel/process.c”声明，由具体的machine代码实现。格式如下：
>   
>  void (\*arm\_pm\_restart)(char str, const char \*cmd) = null\_restart;
>   
>  EXPORT\_SYMBOL\_GPL(arm\_pm\_restart);
>
> 3）等待1s；
>
> 4）如果没有返回，则restart成功，否则失败，打印错误信息。

###### 4.5.2 machine\_halt

ARM的halt很简单，就是将其它CPU停下来，并禁止当前CPU的中断后，死循环！确实，中断被禁止了，又死循环了，不halt才怪。代码如下：

```
   1: /*
```

```
   2:  * Halting simply requires that the secondary CPUs stop performing any
```

```
   3:  * activity (executing tasks, handling interrupts). smp_send_stop()
```

```
   4:  * achieves this.
```

```
   5:  */
```

```
   6: void machine_halt(void)
```

```
   7: {
```

```
   8:         smp_send_stop();
```

```
   9:  
```

```
  10:         local_irq_disable();
```

```
  11:         while (1);
```

```
  12: }
```

###### 4.5.3 machine\_power\_off

power off动作和restart类似，即停止其它CPU，调用回调函数。power off的回调函数和restart类似，就不再说明了。

#### 5. 总结与思考

##### 5.1 Architecture和Machine的概念

本文是我们在分析Linux内核时第一次遇到Architecture和Machine的概念，顺便解释一下。内核代码中最常见的目录结构就是：arch/xxx/mach-xxx/（例如arch/arm/mach-bcm/）。由该目录结构可知，Architecture（简称arch）是指具体的体系结构，如ARM、X86等等。Machine呢，是指具体体系结构下的一个或一系列的SOC，如bcm等。

##### 5.2 电源管理驱动（和reboot有关的部分）需要实现内容

由上面的分析可知，在Reboot的过程中，大部分的逻辑是否内核处理的，具体的driver需要关注2点即可：

1）实现各自的shutdown接口，以正确关闭对应的设备

2）实现machine-dependent的接口，以确保底层的Machine可以正确restart或者power off

看来还是很简单的。

*原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/pm_subsystem/reboot.html)。*
