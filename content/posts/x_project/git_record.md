---
title: "X-001-PRE-git介绍及操作记录"
date: 2016-04-26T22:27:01+08:00
url: "/x_project/git_record.html"
gid: "290"
emlog_type: "blog"
summary: "git是一个高效、实用的版本管理工具，但并不是一个容易掌握的工具，刚接触的时候，总有一种云里雾里的感觉。因此本文将结合“X Project”的开发过程，记录git的操作记录，从实战的角度，理解并学习git。 注1：有关“X Project”的介绍和讨论，可参考“ /forum/ ”。"
author: "wowo"
category: "X Project"
category_alias: "x_project"
tags: ["git", "remote", "push", "origin", "commit"]
views: 17478
comment_count: 17
aliases:
  - "/x_project/290.html"
  - "/290.html"
---

#### 1. 前言

git是一个高效、实用的版本管理工具，但并不是一个容易掌握的工具，刚接触的时候，总有一种云里雾里的感觉。因此本文将结合“X Project”的开发过程，记录git的操作记录，从实战的角度，理解并学习git。

注1：有关“X Project”的介绍和讨论，可参考“[/forum/](/forum/2.html)”。

#### 2. git基础

git是一个分布式的版本管理工具，我们分别从版本管理和分布式两个角度，理解git的原理。

##### 2.1 版本管理

###### 2.1.1 基本概念

git版本管理的思路非常简单：

> 使用一个“链表”，记录仓库里每一次的“修改记录”。

“修改记录”其实就是每一次提交（commit）所对应的一个patch（做linux工程师对patch应该都不陌生），git会根据patch的内容，计算一个40bytes的SHA-1字符串，用来唯一标识这次提交。因此，git版本记录的过程过程可以由一个个串起来的commit表示，例如（以“[https://github.com/wowotechX/u-boot/commits/master](https://github.com/wowotechX/u-boot/commits/master "https://github.com/wowotechX/u-boot/commits/master")”中的提交记录为例，其中右边为最新提交，SHA1字符串只截取了前面6个字符）：

[![git_commit](/content/uploadfile/201604/c3ef5d6ed070f776f68b0ba9772ab51420160426143510.gif "git_commit")](/content/uploadfile/201604/5ef358ae6ad8a50f2d81c107b2f048b920160426143509.gif)

图片1 git的commit链表

【总结】，和提交有关的git命令包括：

> git commit，提交更新
>
> git log，查看提交记录

###### 2.1.2 分支（branch）

上面提到的“用于保存commit记录的链表”是可以被命名的，它就是我们常说的分支，如master分支（可以当作一个链表头，指向最新一次commit）：

[![git_master](/content/uploadfile/201604/eedb73e657a30db1c1662b6615b7b41820160426143515.gif "git_master")](/content/uploadfile/201604/a4d3f040d40dd9ee78daa9bc2892e20020160426143511.gif)

图片2 git的分支（master）

当然，一个仓库中可以同时存在多个分支，我们可以基于任何一次提交，新建一个分支，并让之后的提交沿着新分支“流动”，如下：

[![git_branch](/content/uploadfile/201604/11b5ede057c1fa2e4c9856c38ca3143520160426143527.gif "git_branch")](/content/uploadfile/201604/a0ce00aaa2a98099797e1cca98307b7a20160426143517.gif)

图片3 git多分支

为了方便，git使用一个称作HEAD的指针，指向当前正在操作的分支（当然，HEAD可以任意切换，指向任何一个分支），如下：

[![git_HEAD](/content/uploadfile/201604/0cad13d8d40a042cbf2f7f7fbb19361720160426143530.gif "git_HEAD")](/content/uploadfile/201604/adfe91bacfd26e61de6c1fc30ea8273220160426143528.gif)

图片4 git HEAD

最后，分支之间，可以自由的合并，例如将bY合并到bX上，然后再把bX合并到master上。

【总结】，和分支有关的git命令包括：

> git branch，创建新分支、查看仓库中有哪些分支、查看当前分支、等等
>
> git check，切换分支、创建并切换分支、等等
>
> git merge，合并分支

###### 2.1.3 其它

由于git仓库是使用“链表”的形式管理各个提交的，随意修改链表头的位置，即可回退到某一个版本上，如下：

[![git_reset](/content/uploadfile/201604/58e9ab37040e64772e5268dc456ed49920160426143534.gif "git_reset")](/content/uploadfile/201604/c21f0891b70fd8809515e0203c4133fa20160426143532.gif)

图片5 git版本回退功能

【总结】，和“回退”有关的git命令包括：

> git reset

##### 2.2 分布式

我们在2.1章节介绍git版本管理的时候，没有提到“服务器”的概念，所有的版本管理操作，都是在本地进行的。这就是git与其它版本管理工具（如CVS、SVN等）最本质的区别所在：分布式。

> 所谓的分布式，是指git仓库不是以client-server的形式组织的，而是以对等的形式，在所有的机器上保存相同的copy（当然，是在各自修改之前），并在需要的时候，同步各自的改动，完成“版本控制”的目的。

假设上面图片4是位于github上的某一个仓库的当前快照，任何人都可以把它copy到自己的电脑上（这个过程称作clone），这时就存在两个一模一样的仓库（和图片4一样，这里就不给出图示了）。

一般情况下，自己电脑上的仓库称作本地仓库（local），github上的仓库，称作远端仓库（remote）。我们可以在本地仓库为所欲为，不用担心影响远端仓库，如下：

[![git_remote_local](/content/uploadfile/201604/ccefebe38036a064cb11ac537329b7a120160426143540.gif "git_remote_local")](/content/uploadfile/201604/c2967842585869d37cc0d66a601bc13c20160426143535.gif)

图片6 远端仓库和本地仓库

> 图片6中，本地仓库删除了master分支的两个提交，并在bX分支上新增了两个提交。当然，在本地仓库的任何修改，都不会影响远端仓库，直到将本地的改动同步到的远端为止。

毫无疑问，如果只是在本地仓库操作，就不能称作“版本管理”了。我们可以通过git push命令，将本地的修改推送到远端，同样，也可以通过git pull/git rebase等命令，将远端的改动同步到本地。

【总结】，和“分布式版本管理”有关的git命令包括：

> git init，在本地新建一个git仓库
>
> git clone，copy git仓库
>
> git push，将本地的改动推送到远端仓库
>
> git fetch，获取远端仓库的更新
>
> git rebase，和git pull类似，不过更智能，可以自动处理一些版本的同步
>
> git remote，为远端仓库起一个别名，以方便在本地操作

##### 2.3 Git References

Git References属于Git内部原理的范畴（可参考“[https://git-scm.com/book/zh/v1/Git-%E5%86%85%E9%83%A8%E5%8E%9F%E7%90%86-Git-References](https://git-scm.com/book/zh/v1/Git-%E5%86%85%E9%83%A8%E5%8E%9F%E7%90%86-Git-References "https://git-scm.com/book/zh/v1/Git-%E5%86%85%E9%83%A8%E5%8E%9F%E7%90%86-Git-References")”），本不想在这里介绍。但下一篇文章（“X-002-PRE-基于Gerrithub的代码审核环境的搭建及使用指南”）会在介绍Gerrit服务器的配置的时候，用到相关的概念，就不得不提及了。

由前面2.1、2.2章节的介绍可知，Git版本管理的内容，是一系列由40bytes SHA-1字符串所代表patch，而Git References，则是对这些字符串的引用（也可以理解为别名）。为什么需要别名呢？因为这些字符串太难记了！

根据使用场景的不同，Git References分为四类：

1）指向最后一次提交的reference

这类reference以“refs/heads/”为前缀，例如“refs/heads/master”。大家应该猜到了，这类reference，其实就是Git的分支（Branch），正因为此，前面2.1小节所描述的各种分支名的全称应该是（省略refs字段）：

> heads/master   
> heads/bX   
> heads/bY

不过由于Git默认分支类reference的前缀是“refs/heads/”，因此平时操作分支的时候，可以把“heads”省去。

2）指向当前分支的reference（HEAD 标记）

这个reference比较特别，它没有指向某一个SHA-1字符串，而是指向某一个分支名，如：

> refs/heads/master

因此，HEAD标记就是当前分支的标记，具体可以参考2.1小节的介绍。

3）指向某一个tag的reference

这类reference以“refs/tags/”为前缀，指向git仓库某一个tag。有关git tag的知识，后面用到的时候再介绍。

4）remote reference

指向远端仓库某个SHA-1字符串的标记（也即远端分支），其格式为：

> refs/remotes/远端仓库名（如origin）/远端分支reference名（如master）

因此，平时我们操作远端分支的时候，所操作的分支名为（以远端master分支为例）：

> remotes/origin/master

其实就是省略掉refs字段的reference名称。

总结：知道了这4类reference的含义，以及命名方式之后，我们对各类git名称，会有更深刻的理解。接下来，就在实践中继续领会吧。

#### 3. 操作记录

上面第二章介绍了一些git的基本知识，本章将会结合“X Project”的git操作，做进一步的解释（也顺便记录下来，方面自己和他人）。

注2：本章内容将会随着项目的推进，实时更新。

#### 3.1 通用操作

##### 3.1.1 配置commit时的用户名和邮箱

我们在使用“git log”命令查看某一个git仓库的commit记录的时候，会看到如下的信息：

> commit 2443d048c28a57bfa63d48a88e2461e2ca3910ab   
> Author: wowotech <wowotech@yeah.net>   
> Date: Sat Apr 23 20:04:49 2016 +0800
>
> Initial commit

其中黄色背景的用户名（wowotech）和邮箱名（[wowotech@yeah.net），是在commit的时候由git工具自动添加的（和git账号的用户名和邮箱没有关系，但为了方便，建议大家设置为一样的）。因此，在第一次commit之前，需要使用git config命令，在本地配置用户名和邮箱，改命令的格式如下：](mailto:“wowotech@yeah.net)

> git config --global user.email "you@example.com"   
> git config --global user.name "Your Name"

##### 3.1.2 创建ssh key

默认情况下，大家使用用户名和密码提交代码，这样做有几个缺点：

> 每次提交代码都需要输入用户名和密码，繁琐；
>
> 每次都输入用户名和密码，容易出现安全问题；
>
> 后面使用Gerrithub提交代码的时候，不允许使用用户名和密码的形式。

因此，有必要使用ssh key的形式，具体方法，可参考：[https://help.github.com/articles/generating-an-ssh-key/](https://help.github.com/articles/generating-an-ssh-key/ "https://help.github.com/articles/generating-an-ssh-key/")

下面是我的一个操作记录：

1）[Generating a new SSH key and adding it to the ssh-agent](https://help.github.com/articles/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent)

> $ ssh-keygen -t rsa -b 4096 -C "…………your e-mail address"   
> Generating public/private rsa key pair.   
> Enter file in which to save the key (/home/Administrator/.ssh/id\_rsa):   
> Created directory '/home/Administrator/.ssh'.   
> Enter passphrase (empty for no passphrase):   
> Enter same passphrase again:   
> Your identification has been saved in /home/Administrator/.ssh/id\_rsa.   
> Your public key has been saved in /home/Administrator/.ssh/id\_rsa.pub.   
> The key fingerprint is:   
> ………………………………yours   
> The key's randomart image is:   
> ……yours

> $ eval $(ssh-agent -s)   
> Agent pid 2016

> $ ssh-add ~/.ssh/id\_rsa   
> Enter passphrase for /home/Administrator/.ssh/id\_rsa:   
> Identity added: /home/Administrator/.ssh/id\_rsa (/home/Administrator/.ssh/id\_rsa)

2）[Adding a new SSH key to your GitHub account](https://help.github.com/articles/adding-a-new-ssh-key-to-your-github-account)

按照上面链接的说明，将“~/.ssh/id\_rsa.pub”文件的内容，拷贝到自己github账号的setting中，setting的链接如下：

[https://github.com/settings/keys](https://github.com/settings/keys "https://github.com/settings/keys")

3）[Testing your SSH connection](https://help.github.com/articles/testing-your-ssh-connection)

按照上述指令，检查是否添加成功。

4）添加成功后，记得使用ssh的方式clone仓库，并提交更新，如下

> git clone [git@github.com:wowotechX/tools.git](mailto:git@github.com:wowotechX/tools.git)
>
> 修改…
>
> $ git push origin master:master   
> Warning: Permanently added the RSA host key for IP address '192.30.252.120' to the list of known hosts.   
> 对象计数中: 3, 完成.   
> Delta compression using up to 2 threads.   
> 压缩对象中: 100% (2/2), 完成.   
> 写入对象中: 100% (3/3), 321 bytes | 0 bytes/s, 完成.   
> Total 3 (delta 0), reused 0 (delta 0)   
> To git@github.com:wowotechX/tools.git   
> 2443d04..478acda master -> master
>
> 不再需要用户名、密码了！

##### 3.2 u-boot仓库的操作记录

###### 3.2.1 在自己的工作目录，新建x\_project目录，并进入该目录（该步骤对所以仓库都适用，后面不再说明）

> mkdir x\_project   
> cd x\_project

###### 3.2.2 使用git clone命令将u-boot仓库从github拷贝到本地

> git clone [https://github.com/wowotechX/u-boot.git](https://github.com/wowotechX/u-boot.git "https://github.com/wowotechX/u-boot.git")

**【解释】**：回忆第二章有关远端仓库的概念，git是一个分布式的版本管理工具，u-boot仓库最初位于“git://git.denx.de/u-boot.git”，后来被我们导入到github的wowotechX组织中（以上可参考“[X-000-PRE-开发环境搭建](/x_project/develop_env.html)”中的描述），已经有一次拷贝了。此时，我们又从github中，把它copy到了本地。

**【解释】**：执行git clone命令的时候，git工具会自动为github上的远端仓库（即“[https://github.com/wowotechX/u-boot.git](https://github.com/wowotechX/u-boot.git "https://github.com/wowotechX/u-boot.git")”）起一个别名，在本地称作“origin”，可以使用git remote命令查看。

> $ git remote   
> origin
>
> $ git remote -v   
> origin <https://github.com/wowotechX/u-boot> (fetch)   
> origin <https://github.com/wowotechX/u-boot> (push)

先记着这个名字，后面会用到。当然，我们也可以根据我们的喜好，修改这个名称，后面使用到了再说。

###### 3.2.3 查看新clone的u-boot仓库的分支信息

> $ git branch -a   
> \* master   
> remotes/origin/HEAD -> origin/master   
> remotes/origin/master   
> …

使用git branch命令，可以查看本地仓库的分支信息，使用git branch -a，则可以同时查看远端仓库的信息（记得上面提到的，git clone的时候，已经自动为clone对象在本地起了一个别名，origin）。

**【解释】**：可以看出，本地仓库只有master，而远端仓库则有多个，其中master是当前仓库（HEAD！！）。git clone的时候，只copy了当前仓库。

###### 3.2.4 新建一个名称为x\_integration分支，并上传到远端

> $ git branch x\_integration
>
> $ git branch -a   
> \* master   
> x\_integration   
> remotes/origin/HEAD -> origin/master   
> remotes/origin/master   
> …
>
> $ git push origin x\_integration   
> Username for '<https://github.com':>  
> Password for '<https://wowotech@github.com':>  
> Total 0 (delta 0), reused 0 (delta 0)   
> To <https://github.com/wowotechX/u-boot>  
> \* [new branch] x\_integration -> x\_integration
>
> $ git branch -a   
> \* master   
> x\_integration   
> remotes/origin/HEAD -> origin/master   
> remotes/origin/master   
> …   
> remotes/origin/x\_integration

**【解释】**：git branch x\_integration创建了一个本地分支，创建之后可以查看本地已经新增了一个分支。然后使用”git push origin x\_integration”命令，将该分支推送到远端，该命令通常的使用格式为：

> git push [远端仓库别名] [本地分支名]:[远端分支名]

其中“远端仓库别名”就是origin（代表[https://github.com/wowotechX/u-boot.git](https://github.com/wowotechX/u-boot.git "https://github.com/wowotechX/u-boot.git")），如果本地分支名和远端分支名相同，使用一个即可。

**【解释】**：git push需要提供远端仓库的用户名和密码，为了减少麻烦，可以使用ssh加密的方式，后面再做说明。

**【解释】**：新建的“x\_integration”分支，用于“X Project”的日常开发，以和u-boot原生的分支区隔开来。我们可以把这个分支设置为远端仓库的主分支：

> 登陆github，查看已经多了名称为“x\_integration”的分支，通过该仓库的setting菜单（[https://github.com/wowotechX/u-boot/settings/branches](https://github.com/wowotechX/u-boot/settings/branches "https://github.com/wowotechX/u-boot/settings/branches")），将默认分支设置为“x\_integration”。以后大家的clone操作，将会直接clone “x\_integration”分支。

注4：大家后续的提交操作，请注意提交到“x\_integration”分支上，命令为：

> git push origin [本地分支名]:x\_integration

##### 3.3 linux仓库的操作记录

TODO

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/x_project/git_record.html)。
