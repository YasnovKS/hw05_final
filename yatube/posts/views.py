from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from yatube.settings import POSTS_AMOUNT
from .forms import CommentForm, PostForm
from .models import Follow, Group, Post, User


def create_pages(request, posts):
    paginator = Paginator(posts, POSTS_AMOUNT)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj


def index(request):
    '''
    Функция возвращает данные
    о последних постах пользователей
    и выводит их через шаблон на
    главную страницу сайта.
    '''
    posts = cache.get('index_page')
    if not posts:
        posts = Post.objects.all()
        cache.set('index_page', posts, 20)
    page_obj = create_pages(request, posts)
    template = 'posts/index.html'
    context = {
        'posts': posts,
        'page_obj': page_obj
    }
    return render(request, template, context)


def group_posts(request, slug):
    '''
    Функция собирает информацию о постах
    пользователей и выводит на страницу сайта,
    соответствующую определенному сообществу.
    '''
    template = 'posts/group_list.html'
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.all()
    page_obj = create_pages(request, posts)
    context = {
        'group': group,
        'posts': posts,
        'page_obj': page_obj
    }
    return render(request, template, context)


def profile(request, username):
    author = get_object_or_404(User, username=username)
    posts = author.posts.all()
    posts_count = posts.count()
    page_obj = create_pages(request, posts)
    following = False
    if request.user.is_authenticated:
        user = get_object_or_404(User, username=request.user.username)
        author_in = Follow.objects.filter(user=user, author=author)
        if author_in:
            following = True
    context = {
        'posts': posts,
        'author': author,
        'count': posts_count,
        'page_obj': page_obj,
        'following': following
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    post_title = post.text
    posts_count = post.author.posts.all().count()
    comments = post.comments.all()
    comment_form = CommentForm()
    context = {
        'post': post,
        'title': post_title,
        'count': posts_count,
        'comments': comments,
        'form': comment_form
    }
    return render(request, 'posts/post_detail_comments.html', context)


@login_required
def post_create(request):
    template = 'posts/create_post.html'
    form = PostForm(request.POST or None,
                    files=request.FILES or None
                    )
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('posts:profile', username=request.user)
    context = {
        'form': form,
    }
    return render(request, template, context)


@login_required
def post_edit(request, post_id):
    template = 'posts/create_post.html'
    post = get_object_or_404(Post, pk=post_id)
    if request.user != post.author:
        return redirect('posts:post_detail', post_id=post_id)
    form = PostForm(request.POST or None,
                    files=request.FILES or None,
                    instance=post
                    )
    context = {
        'form': form,
        'is_edit': True,
    }
    if form.is_valid():
        form.save()
        return redirect('posts:post_detail', post_id=post_id)
    return render(request, template, context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    user = get_object_or_404(User, username=request.user.username)
    authors = user.follower.all()
    posts = []
    for author in authors:
        authors_posts = author.author.posts.all()
        for authors_post in authors_posts:
            posts.append(authors_post)
    page_obj = create_pages(request, posts)
    template = 'posts/follow.html'
    context = {
        'posts': posts,
        'page_obj': page_obj
    }
    return render(request, template, context)


@login_required
def profile_follow(request, username):
    user = get_object_or_404(User, username=request.user.username)
    author = get_object_or_404(User, username=username)
    if user != author:
        if not Follow.objects.filter(user=user, author=author):
            Follow.objects.create(user=user,
                                  author=author
                                  )
    return redirect('posts:profile', username)


@login_required
def profile_unfollow(request, username):
    user = get_object_or_404(User, username=request.user.username)
    author = get_object_or_404(User, username=username)
    Follow.objects.filter(user=user,
                          author=author).delete()
    return redirect('posts:profile', username)
