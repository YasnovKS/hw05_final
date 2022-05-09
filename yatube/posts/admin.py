from django.contrib import admin

from .models import Comment, Follow, Group, Post


class PostAdmin(admin.ModelAdmin):
    list_display = ['pk', 'text', 'pub_date', 'author', 'group']
    search_fields = ['text']
    list_filter = ['pub_date']
    list_editable = ['group']
    empty_value_display = '-пусто-'


class GroupAdmin(admin.ModelAdmin):
    list_display = ['title']
    prepopulated_fields = {
        "slug": ("title",)
    }


class CommentAdmin(admin.ModelAdmin):
    list_display = ['text', 'author', 'post', 'created']
    search_fields = ['text', 'author', 'post']
    list_filter = ['created']


admin.site.register(Comment, CommentAdmin)
admin.site.register(Follow)
admin.site.register(Post, PostAdmin)
admin.site.register(Group, GroupAdmin)
