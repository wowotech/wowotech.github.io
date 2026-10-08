---
title: "ACCESS_ONCE宏定义的解释"
date: 2014-07-17T12:34:37+08:00
url: "/process_management/access-once.html"
gid: "66"
emlog_type: "blog"
summary: "在阅读RCU代码的时候遇到了ACCESS_ONCE这个宏定义，感觉比较有意思，因此独立出来一篇文档来描述它。"
author: "linuxer"
category: "进程管理"
category_alias: "process_management"
tags: ["ACCESS_ONCE"]
views: 22979
comment_count: 0
aliases:
  - "/process_management/66.html"
  - "/66.html"
---

一、ACCESS\_ONCE解决什么样的问题

我们首先来看一个代码片段（来自\_\_mutex\_lock\_common函数，位于linux/kernel/locking/mutex.c文件）：

> 例子1
>
> for (;;) {   
> struct task\_struct \*owner;
>
> owner = ACCESS\_ONCE(lock->owner);   
> if (owner && !mutex\_spin\_on\_owner(lock, owner))   
> goto slowpath;   
> /\* ... \*/   
> }

这段代码的逻辑比较简单，主要是为临界区加上mutext锁的操作，当已经有其他的thread持有锁的时候，调用本次加锁操作的进程有两个选择：

1、spin直到获取到mutex锁

2、sleep

不同的场景走不同的分支。如果该锁没有pending waiter并且持有锁的thread在另外一个CPU上运行。这种情况下，spin方案会比较好，因此该锁很可能在随后的短时间内被释放。否则，就需要走到slow path去了。因此，在spin的情况下，代码会不断的轮询lock->owner并判断是否owner还持有锁资源，如果当前的owner还占用该资源，那么继续polling，如果锁被释放了，那么程序可以获得锁资源并继续向下执行。c代码虽然好理解，不过c代码和CPU真正执行的代码指令之间还有一个编译器，有些编译器会不择手段的进行优化。例如，对于上面的代码，lock->owner这个变量在for循环中并没有被修改，那么编译器就认为CPU不需要在每一个循环中访问该变量，因此这段代码有可能被编译器优化成：

> struct task\_struct \*owner;
>
> owner = ACCESS\_ONCE(lock->owner);
>
> for (;;) {   
> if (owner && !mutex\_spin\_on\_owner(lock, owner))   
> break;   
> /\* ... \*/   
> }

编译器其实没有那么智能，如果不告诉它，它在编译c代码的时候总是缺省认为只有一个thread在该地址空间中执行。因此，编译器并不知道lock->owner有可能被其他的thread修改的这个事实，因此作出错误的优化（对于single thread，这个优化无疑是正确的）。

在这个例子中，ACCESS\_ONCE被c code用来告知编译器在编译的时候，不要因为优化而将多次内存访问合并称为一次。对lock->owner这个memory的访问要确保每个循环都access once。

我们再看另外一个代码片段的例子（来自Linus的邮件）：

> 例子2
>
> if (a > MEMORY) {   
> do1;   
> do2;   
> do3;   
> } else {   
> do2;   
> }

这段代码可能被编译器优化成：

> if (a > MEMORY)   
> do1;   
> do2;   
> if (a > MEMORY)   
> do3;

但是，对于优化后的代码，如果有其他的thread在执行do2的时候修改了MEMORY的值，这时候，CPU执行的代码逻辑和c code是不一致的，或许就会导致问题。

在这个例子中，ACCESS\_ONCE这个名字解释就更好理解。也就是说，编译器在编译的时候，不要因为优化而将内存访问拆成多次，确保该内存访问是access once而不是access multi times。

综上所述，ACCESS\_ONCE就是用来让c code告诉编译器，这里的内存访问不要优化（不要将多次内存访问合并，对应例子1，也不要将一次内存访问分拆成多次，对应例子2）。

二、代码实现

本身ACCESS\_ONCE非常简单，如下：

> #define ACCESS\_ONCE(x) (\*(volatile typeof(x) \*)&(x))

ACCESS\_ONCE本身的实现就是增加了volatile这个关键字，它确保编译器每次访问变量x都是从内存中获取。

*原创文章，转发请注明出处。蜗窝科技，[/process_management/access-once.html](/process_management/access-once.html)*
