---
title: "X-022-OTHERS-git操作记录之合并远端分支的更新"
date: 2017-01-02T22:26:22+08:00
url: "/x_project/u_boot_merge_denx.html"
gid: "366"
emlog_type: "blog"
summary: "本文将以“ X Project ”的开发过程为例，介绍“合并远端分支的更新”的方法。事情的起因如下： “ X Project ”是一个学习嵌入式Linux开发全过程的小项目，项目开始的时候，u-boot、linux kernel等代码，都是直接从官方仓库的当前状态获取的(具体可参考[2]）。以u-boot为例，“ X Project ”的u-boot [3] 是2016年4月23日从u-boot的"
author: "wowo"
category: "X Project"
category_alias: "x_project"
tags: ["git", "remote", "u-boot", "merge", "denx", "add"]
views: 7401
comment_count: 0
aliases:
  - "/x_project/366.html"
  - "/366.html"
---

## 1. 前言

本文将以“[X Project](/sort/x_project)”的开发过程为例，介绍“合并远端分支的更新”的方法。事情的起因如下：

> “[X Project](/sort/x_project)”是一个学习嵌入式Linux开发全过程的小项目，项目开始的时候，u-boot、linux kernel等代码，都是直接从官方仓库的当前状态获取的(具体可参考[2]）。以u-boot为例，“[X Project](/sort/x_project)”的u-boot[3]是2016年4月23日从u-boot的官方仓库[1]拷贝而来的。
>
> 随着时间的推移，官方仓库可能有很多更新，例如修复bug、添加新功能等，在合适的时间点，需要将这些更新合并。下面就以“[X Project](/sort/x_project)”的u-boot为例，介绍合并的步骤。

## 2. 操作原理

我们知道，git是一种分布式的版本管理工具。所谓的分布式，是指代码仓库可以保存在多个地方，例如保存在本地计算机中的，称作本地仓库（local），保存在服务器上的，称作远端仓库（remote）。我们使用git clone命令从远端下载仓库到本地后，git会将该远端仓库在本地保存为名称为origin的引用，以“[X Project](/sort/x_project)”的u-boot为例，如下：

> pengo@ubuntu:~/work/xprj/u-boot$ git remote show   
> origin

当然，我们可以使用git remote add命令，将多个远端仓库添加到本地的索引中，同样以u-boot为例，我们可以将u-boot的官方仓库[1]添加进来（命令的具体用法，请参考git的帮助文档）：

> pengo@ubuntu:~/work/xprj/u-boot$ git remote add denx <http://git.denx.de/u-boot.git>
>
> pengo@ubuntu:~/work/xprj/u-boot$ git remote show   
> denx  
> origin

其实，“[X Project](/sort/x_project)”新建u-boot的仓库时，就是先从denx仓库clone到origin仓库，然后下载到本地仓库中，如下图所示：

[![git_remote_merge](/content/uploadfile/201701/5b699a4963d85a6113d30c0948d0bd2e20170102142621.gif "git_remote_merge")](/content/uploadfile/201701/ae4eafed3b8ae21924cb1be6f64bc5b620170102142620.gif)

本文所需要做的，就是将denx仓库中master分支的改动，更新（合并）到origin仓库的master和x\_intergration分支中。具体步骤请参考下面章节。

## 3. 操作步骤

#### 3.1 添加denx远端仓库

1）在本地查看当前默认的远端仓库（origin）及其分支

> pengo@ubuntu:~/work/xprj/u-boot$ git remote show   
> origin
>
> pengo@ubuntu:~/work/xprj/u-boot$ git branch -r   
> origin/HEAD -> origin/x\_integration   
> origin/hikey   
> origin/master   
> origin/next   
> origin/origin   
> origin/tiny210   
> origin/u-boot-2009.11.y   
> origin/u-boot-2013.01.y   
> origin/x\_integration

2）添加denx远端仓库并查看其信息

> pengo@ubuntu:~/work/xprj/u-boot$ git remote add denx <http://git.denx.de/u-boot.git>
>
> pengo@ubuntu:~/work/xprj/u-boot$ git remote show   
> denx  
> origin
>
> pengo@ubuntu:~/work/xprj/u-boot$ git remote show denx
>
> \* remote denx   
> Fetch URL: <http://git.denx.de/u-boot.git>  
> Push URL: <http://git.denx.de/u-boot.git>  
> HEAD branch: master   
> Remote branches:   
> master new (next fetch will store in remotes/denx)   
> next new (next fetch will store in remotes/denx)   
> origin new (next fetch will store in remotes/denx)   
> u-boot-2009.11.y new (next fetch will store in remotes/denx)   
> u-boot-2013.01.y new (next fetch will store in remotes/denx)   
> u-boot-2016.09.y new (next fetch will store in remotes/denx)

3）获取远端仓库的分支信息

> pengo@ubuntu:~/work/xprj/u-boot$ git fetch denx  
> From <http://git.denx.de/u-boot>  
> \* [new branch] master -> denx/master   
> \* [new branch] next -> denx/next   
> \* [new branch] origin -> denx/origin   
> \* [new branch] u-boot-2009.11.y -> denx/u-boot-2009.11.y   
> \* [new branch] u-boot-2013.01.y -> denx/u-boot-2013.01.y   
> \* [new branch] u-boot-2016.09.y -> denx/u-boot-2016.09.y   
> \* [new tag] v2016.05 -> v2016.05   
> \* [new tag] v2016.05-rc3 -> v2016.05-rc3   
> \* [new tag] v2016.07 -> v2016.07   
> \* [new tag] v2016.07-rc1 -> v2016.07-rc1   
> \* [new tag] v2016.07-rc2 -> v2016.07-rc2   
> \* [new tag] v2016.07-rc3 -> v2016.07-rc3   
> \* [new tag] v2016.09 -> v2016.09   
> \* [new tag] v2016.09-rc1 -> v2016.09-rc1   
> \* [new tag] v2016.09-rc2 -> v2016.09-rc2   
> \* [new tag] v2016.09.01 -> v2016.09.01   
> \* [new tag] v2016.11 -> v2016.11   
> \* [new tag] v2016.11-rc1 -> v2016.11-rc1   
> \* [new tag] v2016.11-rc2 -> v2016.11-rc2   
> \* [new tag] v2016.11-rc3 -> v2016.11-rc3   
> \* [new tag] v2017.01-rc1 -> v2017.01-rc1   
> \* [new tag] v2017.01-rc2 -> v2017.01-rc2

4）查看获取后的分支信息（已经出现新添加的远端仓库的信息）

> pengo@ubuntu:~/work/xprj/u-boot$ git branch -r   
> denx/master   
> denx/next   
> denx/origin   
> denx/u-boot-2009.11.y   
> denx/u-boot-2013.01.y   
> denx/u-boot-2016.09.y  
> origin/HEAD -> origin/x\_integration   
> origin/hikey   
> origin/master   
> origin/next   
> origin/origin   
> origin/tiny210   
> origin/u-boot-2009.11.y   
> origin/u-boot-2013.01.y   
> origin/x\_integration

#### 3.2 将denx/master合并到origin/master

1）基于origin/master新建一个本地分支xdev\_merge，并checkout到该分支

> pengo@ubuntu:~/work/xprj/u-boot$ git checkout origin/master -b xdev\_merge   
> Branch xdev\_merge set up to track remote branch master from origin.   
> Switched to a new branch 'xdev\_merge'

2）将denx/master合并到本地分支上

> pengo@ubuntu:~/work/xprj/u-boot$ git merge denx/master   
> …

注1：由于origin/master完全是denx/master的一个快照，没有任何改动，因此merge不会产生任何冲突。

3）查看合并后的日志（合并成功）

> pengo@ubuntu:~/work/xprj/u-boot$ git log   
> commit 3d3a74cc8c774345be7d1661b215555ad41f4515   
> Author: Masahiro Yamada <yamada.masahiro@socionext.com>   
> Date: Wed Dec 7 22:10:30 2016 +0900   
> mmc: move MMC\_SDHCI\_IO\_ACCESSORS to Kconfig   
> ..

4）将合并后的本地分支提交到origin/master，工作完成

> pengo@ubuntu:~/work/xprj/u-boot$ git push origin xdev\_merge:master   
> Password:   
> Counting objects: 56980, done.   
> Compressing objects: 100% (8730/8730), done.   
> Writing objects: 100% (52590/52590), 9.76 MiB | 224 KiB/s, done.   
> Total 52590 (delta 44572), reused 51261 (delta 43413)   
> remote: Resolving deltas: 100% (44572/44572), completed with 2815 local objects.   
> To [https://](https://pengoor@github.com/wowotechX/u-boot.git)pengoor@github.com/wowotechX/u-boot.git   
> ee8b25f..3d3a74c xdev\_merge -> master

#### 3.3 将denx/master合并到“[X Project](/sort/x_project)”的开发分支（origin/x\_integration）

1）基于origin/x\_integration新建一个本地分支xdev\_merge，并checkout到该分支（步骤略）。

2）将denx/master合并到本地分支上（步骤略）。

3）合并的过程中，会有冲突，如下：

> pengo@ubuntu:~/work/xprj/u-boot$ git status   
> # On branch xdev   
> # Changes to be committed:   
> #   
> # modified: .mailmap   
> # modified: .travis.yml   
> # modified: Kconfig   
> …   
> # Unmerged paths:   
> # (use "git add/rm ..." as appropriate to mark resolution)   
> #   
> # both modified: arch/arm/dts/Makefile   
> # both modified: drivers/gpio/s5p\_gpio.c   
> # both modified: drivers/pinctrl/Makefile   
> # both modified: drivers/serial/Kconfig   
> # both modified: drivers/serial/Makefile   
> #

需要解决冲突，具体的解决过程（就是修改指定的冲突文件）不再详细说明，需要注意的时，冲突解决后，需要使用git add告诉git工具冲突已解决，例如：

> pengo@ubuntu:~/work/xprj/u-boot$ git add arch/arm/dts/Makefile

最后，全家解决完毕后，调用git commit提交这次merge的内容：

> pengo@ubuntu:~/work/xprj/u-boot$ git commit
>
> 直接提交，日志也不用改。。。。

4）最后，尝试编译，并解决编译错误（过程略，具体可参考下面的patch）

> [https://github.com/wowotechX/u-boot/commit/7401205742ac88d1e4bc25a216c88d03d7fa9315](https://github.com/wowotechX/u-boot/commit/7401205742ac88d1e4bc25a216c88d03d7fa9315 "https://github.com/wowotechX/u-boot/commit/7401205742ac88d1e4bc25a216c88d03d7fa9315")

5）下载到板子上，验证ok后，将本地分支提交到origin/x\_integration即可

> pengo@ubuntu:~/work/xprj/u-boot$ git push origin xdev\_merge:x\_integration   
> Password:   
> Counting objects: 89, done.   
> Compressing objects: 100% (34/34), done.   
> …

## 4. 参考文档

[1] <http://git.denx.de/u-boot.git>

[2] [X-000-PRE-开发环境搭建](/x_project/develop_env.html)

[3] [https://github.com/wowotechX/u-boot](https://github.com/wowotechX/u-boot "https://github.com/wowotechX/u-boot")

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/x_project/u_boot_merge_denx.html)。
