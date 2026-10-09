---
title: "ARM Linux上的系统调用代码分析"
date: 2017-02-20T18:54:18+08:00
url: "/process_management/syscall-arm.html"
gid: "377"
emlog_type: "blog"
summary: "当用户空间的程序调用swi指令发起内核服务请求的时候，实际上程序其实是完成了一次“穿越”，该进程从用户态穿越到了内核态。这个过程有点象周末你在家里看片，突然有些内急，随手按下了pause按键，电影里面的世界嘎然而止了。程序世界亦然，一个swi后，用户空间的代码执行暂停了、stack（用户栈）上的数据，正文段、静态数据区、heap去的数据……一切都停下来了，程序的执行突然就转入另外一个世界，使用的栈"
author: "linuxer"
category: "进程管理"
category_alias: "process_management"
tags: ["ARM", "系统调用"]
views: 23863
comment_count: 8
aliases:
  - "/process_management/377.html"
  - "/377.html"
---

一、前言

当用户空间的程序调用swi指令发起内核服务请求的时候，实际上程序其实是完成了一次“穿越”，该进程从用户态穿越到了内核态。这个过程有点象周末你在家里看片，突然有些内急，随手按下了pause按键，电影里面的世界嘎然而止了。程序世界亦然，一个swi后，用户空间的代码执行暂停了、stack（用户栈）上的数据，正文段、静态数据区、heap去的数据……一切都停下来了，程序的执行突然就转入另外一个世界，使用的栈变成了内核栈、正在执行的正文段程序变成vector\_swi开始的binary code、与之匹配数据区也变化了……

一切是怎么发生的呢？CPU只有一套而已，这里硬件做了哪些动作？软件又搞了什么鬼？穿越到另外的世界当然有趣，但是如何找到回来的路？这一切疑问希望能在这样的一篇文档中讲述清楚。

本文的代码来自4.4.6内核，用ARM处理器为例子描述。

二、构建内核栈上的用户现场

代码如下（忽略Cortex-M处理器的代码，忽略THUMB指令集的代码）：

> ENTRY(vector\_swi)   
> sub sp, sp, #S\_FRAME\_SIZE   
> stmia sp, {r0 - r12} @ Calling r0 - r12   
> ARM( add r8, sp, #S\_PC )   
> ARM( stmdb r8, {sp, lr}^ ) @ Calling sp, lr   
> mrs r8, spsr @ called from non-FIQ mode, so ok.   
> str lr, [sp, #S\_PC] @ Save calling PC   
> str r8, [sp, #S\_PSR] @ Save CPSR   
> str r0, [sp, #S\_OLD\_R0] @ Save OLD\_R0

当执行vector\_swi的时候，硬件已经做了不少的事情，包括：

（1）将CPSR寄存器保存到SPSR\_svc寄存器中，将返回地址（用户空间执行swi指令的下一条指令）保存在lr\_svc中

（2）设定CPSR寄存器的值。具体包括：CPSR.M = '10011'（svc mode），CPSR.I = '1'（disable IRQ），CPSR.IT = '00000000'（TODO），CPSR.J = '0'（），CPSR.T = SCTLR.TE（J和Tbit和Instruction set state有关，和本文无关），CPSR.E = SCTLR.EE（字节序定义，和本文无关）。

（3）PC设定为swi异常向量的地址

随后的行为都是软件行为了，因为代码中涉及压栈动作，所以首先要确定的就是当前在哪里这个问题。sp\_svc早在进程切换的时候就已经设定好了，就是该进程的内核栈。

[![未命名](/content/uploadfile/201702/8991a20bccab1926173bf8d0cb89bdeb20170220105413.gif "未命名")](/content/uploadfile/201702/575e0854debf480cdbe72e46c1ed798e20170220105412.gif)

当Task A切换到Task B的时候，有一个很重要的步骤就是HW context的切换，由于Task A和Task B都在同一个CPU上运行，因此需要把当前CPU的各种寄存器以及状态信息保存在一块memory data block中（也就是硬件上下文了），并且用Task B的硬件上下文的数值来加载CPU，这里面就包括sp\_svc。在内核态，完成进程切换后，最终会返回task B的用户空间执行，但是这时候Task B对应的内核栈（sp\_svc0）是确定的了。

当通过系统调用进入内核的时候，内核栈已经是准备好了，不过这时候内核栈上是空的，执行完上述代码之后，在内核栈上形成如下的用户空间现场：

[![systemcall](/content/uploadfile/201702/fa2dc3f37b146150f55d11a02958133f20170220105416.gif "systemcall")](/content/uploadfile/201702/05d69dcd09b64cf10ad06973533e6a1720170220105414.gif)

代码我们就不走读了，很简单，大家可自行阅读即可。顺便一提的是：你看到这个保存的现场是不是觉得很熟悉？可以看看[ARM中断处理](/irq_subsystem/irq_handler.html)这篇文档，中断保存的现场和系统调用是一样的。另外，保存在内核栈上的用户空间现场并不是全部的HW Context，HW context是一段内存中的数据，保存了某个时刻CPU的全部状态，不仅仅是core register，还有很多CPU内部其他的HW block状态，例如FPU的寄存器和状态。这时候，问题来了，在通过系统调用进入内核态的时候，仅仅保存core register够不够？够不够是和系统调用接口的约定相关，实际上，对于linux，我们约定如下：内核态的代码是不允许执行浮点操作指令的（这里用FPU例子，其他类似），如果一定要这样的话，那么需要在内核使用FPU的代码前后增加FPU上下文的保存和恢复的代码，确保在返回用户空间的时候，FPU的上下文是保持不变的。

最后一个有趣的问题是：为何r0被两次压栈？一个是r0，另外一个是old r0。其实在系统调用过程中，r0有两个角色，一个是传递参数，另外一个是返回值。刚进入系统调用现场的时候，old r0和r0其实都是保存了本次系统调用的参数，而在完成系统调用之后，r0保存了返回用户空间的return value。不过你可能觉得用一个r0就OK了，具体为何如此我们后面还会进行描述。

三、几个简单的初始化操作

代码如下：

> zero\_fp   
> alignment\_trap r10, ip, \_\_cr\_alignment   
> enable\_irq   
> ct\_user\_exit   
> get\_thread\_info tsk

zero\_fp用来清除frame pointer，在debugger做栈的回溯的时候，当fp等于0的时候也就意味着到了最外层函数。对于kernel而言，来到这里，函数的调用跟踪就结束了，我们不可能一直回溯到用户空间的函数调用。上一节，我们说过了，硬件会关闭irq，在这里，我们通过enable\_irq开启本cpu的中断处理。ct\_user\_exit和Context tracking subsystem相关的内容，这里就不深入了，关于对齐，可以多聊几句。ARM64的硬件是支持非对齐操作的，当然仅仅限于对normal memory的访问（对memory order没有要求的那些访问，例如exclusive load/store和load-acquire 或者 store-release 指令就不支持了）。由于取指而产生的内存访问或者是访问device type的memory都是必须要对齐的。当指令是非对齐的访问的时候，可以有两个选择（SCTLR\_ELx.A控制）：一个是产生fault，另外一个是执行非对齐访问（由硬件完成）。对内存的非对齐的访问在总线上被分解成两个transaction。所有的ARMv8的处理器的硬件都支持非对齐访问，因此，在ARM64应该不需要软件来实现非对齐的访问。

支持ARMv8的处理器当然不需要考虑对齐问题，不过对于ARM processor，有些硬件是不支持非对齐的访问的，这时候，内核配置（CONFIG\_ALIGNMENT\_TRAP）可以用软件的方法来实现非对齐访问（这是在硬件不支持的情况下的无奈之举），但是对性能的杀伤力极大，不到万不得已不能打开。具体代码很简单，这里就不说明了。

三、如何获取系统调用号？

系统调用有两种规范，一种是老的OABI（系统调用号来自swi指令中），另外一种是ARM ABI，也就是EABI（系统调用号来自r7）。如果想要兼容旧的OABI，那么我们需要定义OABI\_COMPAT，这会带来一点系统调用的开销，同时让内核变大一点，对应的好处是使用旧的OABI规格的用户程序也可以运行在内核之上。当然，如果我们确定用户空间只是服从EABI规范，那么可以考虑不定义CONFIG\_OABI\_COMPAT。

相关的代码如下：

> #if defined(CONFIG\_OABI\_COMPAT)   
>   
> USER( ldr r10, [lr, #-4] ) @ get SWI instruction   
> ARM\_BE8(rev r10, r10) @ little endian instruction
>
> #elif defined(CONFIG\_AEABI)
>
> #else   
> /\* Legacy ABI only. \*/   
> USER( ldr scno, [lr, #-4] ) @ get SWI instruction   
> #endif

如果是符合EABI规范，那么直接从r7中获取系统调用号即可，不需要特别的代码，因此CONFIG\_AEABI的情况下，代码是空的。如果是老的规范，那么我们需要从SWI指令那里获取系统调用号，这时候，我们需要lr（实际上就是lr\_svc，该寄存器保存了swi指令的下一条指令）来找到swi那一条指令码。

> uaccess\_disable tbl
>
> adr tbl, sys\_call\_table @ load syscall table pointer
>
> #if defined(CONFIG\_OABI\_COMPAT)   
> bics r10, r10, #0xff000000   
> eorne scno, r10, #\_\_NR\_OABI\_SYSCALL\_BASE   
> ldrne tbl, =sys\_oabi\_call\_table   
> #elif !defined(CONFIG\_AEABI)   
> bic scno, scno, #0xff000000 @ mask off SWI op-code   
> eor scno, scno, #\_\_NR\_SYSCALL\_BASE @ check OS number   
> #endif

取出swi指令中的低24bit就可以得出系统调用号，当然，对于EABI标准，我们使用r7传递系统调用号，因此陷入内核的时候永远使用“swi 0”这样的方式，因此，如果swi指令中的低24bit是0，则说明是服从EABI规范。

执行完上面的代码后，r7（scno）中保存了系统调用号，r8（tbl）中是syscall table pointer，通过r7和r8的值，我们已经知道后续的路该如何走了。

四、参数传递

使用swi指令的代码位于glibc中，我们可以大概把代码认为是如下的格式：

> ……
>
> return value = swi( 参数1，参数2，……);
>
> ……

从这个角度看，系统调用和一个普通的c程序调用是类似的，都有参数和返回值的概念。当然，由于模式也发生了切换，因此这里的参数传递不能使用stack压栈的方式（swi产生了stack的切换），只能使用寄存器的方式。

对于ARM处理器，标准过程调用约定使用r0～r3来传递参数，其余的参数压入栈中。经过前面两个小节的描述，我们已经找到系统调用号和系统调用表，下面准备调用内核的系统调用函数，对于内核态的系统调用函数，其格式如下：

> ……
>
> return value = sys\_xxx( 参数1，参数2，……);
>
> ……

因此，我们还需要点代码来过渡到sys\_xxx，如下：

> local\_restart:   
> ldr r10, [tsk, #TI\_FLAGS] @ check for syscall tracing   
> stmdb sp!, {r4, r5} @ push fifth and sixth args
>
> tst r10, #\_TIF\_SYSCALL\_WORK @ are we tracing syscalls?   
> bne \_\_sys\_trace
>
> cmp scno, #NR\_syscalls @ check upper syscall limit   
> badr lr, ret\_fast\_syscall @ return address   
> ldrcc pc, [tbl, scno, lsl #2] @ call sys\_\* routine

我们这里需要模拟一个c函数调用，因此需要在栈上压入系统调用可能存在的第五和第六个参数（有些系统调用超过4个参数，他们使用r0～r5在swi接口上传递参数）。如果参数OK的话，那么ldrcc pc, [tbl, scno, lsl #2]代码将直接把控制权交给对应的sys\_xxx函数。需要注意的是返回地址的设定，我们无法使用bl这样的汇编指令，因此只能是手动设定lr寄存器了（badr lr, ret\_fast\_syscall ）。

五、返回用户空间

在返回用户空间之前会处理很多的事情，例如信号处理、进程调度等，这是通过检查struct thread\_info中的flag标记来完成的，代码如下：

> disable\_irq\_notrace @ disable interrupts   
> ldr r1, [tsk, #TI\_FLAGS] @ re-check for syscall tracing   
> tst r1, #\_TIF\_SYSCALL\_WORK | \_TIF\_WORK\_MASK   
> bne fast\_work\_pending
>
> restore\_user\_regs fast = 1, offset = S\_OFF
>
> fast\_work\_pending:   
> str r0, [sp, #S\_R0+S\_OFF]! @ returned r0
>
> ……

这里面最著名的flag就是\_TIF\_NEED\_RESCHED，有了这个flag，说明有调度需求。由此可知在系统调用返回用户空间的时候上有一个调度点。其他的flag和我们这里的场景无关，这里就不描述了，总而言之，如果需要有其他额外的事情要处理，我们需要跳转到fast\_work\_pending ，否则调用restore\_user\_regs返回用户空间现场。这里有一个小小的细节：如果需要有额外的事项处理（例如有pending signal），那么r0寄存器实际上会被破坏掉，也就破坏了sys\_xxx函数的返回值，这时候，我们把r0保存到了用户现场（pt\_regs）中的S\_R0的位置，这也是为何pt\_regs有S\_R0和S\_OLD\_R0两个和r0相关的域。

恢复用户空间的代码（restore\_user\_regs ）如下：

> mov r2, sp   
> ldr r1, [r2, #\offset + S\_PSR] @ get calling cpsr   
> ldr lr, [r2, #\offset + S\_PC]! @ get pc   
> msr spsr\_cxsf, r1 @ save in spsr\_svc   
> .if \fast   
> ldmdb r2, {r1 - lr}^ @ get calling r1 - lr   
> .else   
> ldmdb r2, {r0 - lr}^ @ get calling r0 - lr   
> .endif   
> mov r0, r0 @ ARMv5T and earlier require a nop   
> @ after ldm {}^   
> add sp, sp, #\offset + S\_FRAME\_SIZE   
> movs pc, lr @ return & move spsr\_svc into cpsr

整个代码比较简单，就是用进入系统调用时候压入内核栈的值来进行用户现场的恢复，其中一个细节是内核栈的操作，在调用movs pc, lr 返回用户空间现场之前，add sp, sp, #\offset + S\_FRAME\_SIZE指令确保用户栈上是空的。此外，我们需要考虑返回用户空间时候的r0设置问题，毕竟它承载了本次系统调用的返回值，这时候的r0有两种情况：

（1）在没有pending work的情况下（fast等于1），r0保存了sys\_xxx函数的返回值

（2）在有pending work的情况下（fast等于0），struct pt\_regs（返回用户空间的现场）中的r0保存了sys\_xxx函数的返回值

restore\_user\_regs还有一个参数叫做offset，我们知道，在进入系统调用的时候，我们把参数5和参数6压入栈上，因此产生了到pt\_regs 8个字节的偏移，这里需要补偿回来。

*原创文章，转发请注明出处。蜗窝科技*
