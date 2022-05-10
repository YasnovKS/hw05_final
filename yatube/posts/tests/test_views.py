import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from yatube.settings import POSTS_AMOUNT
from ..models import Group, Post, Follow

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

User = get_user_model()

TEST_IMAGE = (b'\x47\x49\x46\x38\x39\x61\x02\x00'
              b'\x01\x00\x80\x00\x00\x00\x00\x00'
              b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
              b'\x00\x00\x00\x2C\x00\x00\x00\x00'
              b'\x02\x00\x01\x00\x00\x02\x02\x0C'
              b'\x0A\x00\x3B'
              )


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class TestPostViews(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        cls.user = User.objects.create(username='Kirill')

        cls.group = Group.objects.create(
            title='Test title',
            description='Test description',
            slug='test-slug'
        )

        cls.another_group = Group.objects.create(
            title='Another title',
            description='Another description',
            slug='another-slug'
        )

        cls.image = SimpleUploadedFile(name='Test.gif',
                                       content=TEST_IMAGE,
                                       content_type='image/gif'
                                       )

        cls.posts = list()
        for i in range(15):
            post = Post(text=f'Post text #{i}',
                        author=cls.user,
                        group=cls.group,
                        image=cls.image)
            cls.posts.append(post)
        Post.objects.bulk_create(cls.posts)

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self) -> None:
        super().setUp()

        self.client = Client()
        self.client.force_login(self.user)

        self.post = Post.objects.all().first()

    def test_views_templates(self):
        '''Проверка использования корректного шаблона'''

        posts_views = {
            'index': {(reverse('posts:index')): 'posts/index.html'},
            'post_create': {(reverse('posts:post_create')):
                            'posts/create_post.html'
                            },
            'group_list': {(reverse('posts:group_list',
                            kwargs={'slug': self.group.slug})):
                           'posts/group_list.html'
                           },
            'profile': {(reverse('posts:profile',
                        args=(self.user.username,))):
                        'posts/profile.html'
                        },
            'post_detail': {(reverse('posts:post_detail',
                            kwargs={'post_id': self.post.id})):
                            'posts/post_detail.html'
                            },
            'post_edit': {(reverse('posts:post_edit',
                          kwargs={'post_id': self.post.id})):
                          'posts/create_post.html'
                          }
        }

        for name, data in posts_views.items():
            for view, template in data.items():
                with self.subTest(name=name):
                    response = self.client.get(view)
                    self.assertTemplateUsed(response,
                                            template,
                                            f'Для страницы {name} '
                                            'используется некорректный шаблон.'
                                            )

    def test_views_context(self):
        '''Проверка корректной передачи объектов в контекст'''

        posts_count = Post.objects.all().count()

        last_page_amount = posts_count % POSTS_AMOUNT
        last_page_number = (posts_count // POSTS_AMOUNT) + 1

        views = {
            'index': reverse('posts:index'),
            'group_list': (reverse('posts:group_list',
                           kwargs={'slug': self.group.slug})),
            'profile': (reverse('posts:profile',
                        kwargs={'username': self.user.username})),
            'post_detail': (reverse('posts:post_detail',
                            kwargs={'post_id': self.post.id}))
        }
        page_list = ["index", "group_list", "profile"]

        for name, view in views.items():
            with self.subTest(name=name):
                response = self.client.get(view)
                pagination = self.client.get(view
                                             + f'?page={last_page_number}')

                if name in page_list:
                    post_object = response.context['posts'].first()
                    page_objects = response.context['page_obj']
                    last_page_objects = pagination.context['page_obj']

                    pages_objects = {
                        page_objects: POSTS_AMOUNT,
                        last_page_objects: last_page_amount
                    }
                    for page, amount in pages_objects.items():
                        self.assertEqual(len(page), amount,
                                         f'На странице {name} некорректно '
                                         'работает paginator')

                else:
                    post_object = response.context['post']

                text = post_object.text
                author = post_object.author.username
                picture = post_object.image

                expected_post_values = {
                    text: self.post.text,
                    author: self.user.username
                }

                for field, value in expected_post_values.items():
                    self.assertEqual(field, value,
                                     f'В поле {field} на странице {name} '
                                     'передается некорректный контекст.'
                                     )
                    self.assertTrue(picture,
                                    'Картинка поста не передается в контекст '
                                    f'на странице {name}')

    def test_form_post_create_or_edit(self):
        '''Проверка соответствия типов полей формы создания
        и редактирования поста'''

        views = {
            'post_edit': (reverse('posts:post_edit',
                          kwargs={'post_id': self.post.id})),
            'post_create': reverse('posts:post_create')
        }
        for view in views.values():
            response = self.client.get(view)
            context = response.context['form']

            form_fields = {
                'text': forms.fields.CharField,
                'group': forms.fields.ChoiceField
            }
            for field, type in form_fields.items():
                with self.subTest(field=field):
                    form_field = context.fields[field]
                    self.assertIsInstance(form_field, type)

    def test_additional_post_create(self):
        '''Тестирование корректного отображения поста с указанием
        группы на страницах, где он должен отображаться, и проверка его
        отсутствия на странице посторонней группы.'''
        views = {
            'index': reverse('posts:index'),
            'group_list': (reverse('posts:group_list',
                           kwargs={'slug': self.group.slug})),
            'profile': (reverse('posts:profile',
                        kwargs={'username': self.user.username}))
        }

        for name, view in views.items():
            with self.subTest(name=name):
                response = self.client.get(view).context['posts']
                self.assertIn(self.post, response)

        response = self.client.get(reverse('posts:group_list',
                                           kwargs={
                                               'slug':
                                               self.another_group.slug
                                           }
                                           )
                                   ).context['posts']
        self.assertNotIn(self.post, response)

    def test_comment_in_context(self):
        post = Post.objects.all().first()

        form = {
            'text': 'Test comment',
            'author': self.user,
            'post': post.id
        }

        self.client.post(reverse('posts:add_comment',
                                 args=(post.id,)
                                 ),
                         form,
                         follow=True
                         )
        response = self.client.get(reverse('posts:post_detail',
                                           args=(post.id,)
                                           )
                                   )
        context = response.context['comments'][0]

        self.assertEqual(context.text, form['text'])


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class TestCache(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        cls.user = User.objects.create(username='User')

        Post.objects.create(text='Test post',
                            author=cls.user)

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self) -> None:
        super().setUp()
        self.client = Client()
        self.client.force_login(self.user)

    def test_cache_working(self):

        response = self.client.get(reverse('posts:index'))
        context = response.context['posts']
        #  Проверяем, что главная страница отдает нам посты:
        self.assertTrue(context)

        #  Проверяем, что кэш после первого запроса сохранился
        #  и существует:

        test_cache = cache.get('index_page')
        self.assertTrue(test_cache)

        #  Удаляем посты и запрашиваем главную страницу заново,
        #  ожидая при этом QuerySet из кэша:
        Post.objects.all().delete()
        response = self.client.get(reverse('posts:index'))
        context = response.context['posts']

        self.assertTrue(context)

        #  Очищаем кэш и запрашиваем контекст (ожидаем пустой
        #  QuerySet):
        cache.delete('index_page')
        response = self.client.get(reverse('posts:index'))
        context = response.context['posts']

        self.assertFalse(context)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class TestFollowing(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.main_user = User.objects.create(username='Kirill')
        cls.author = User.objects.create(username='Author')
        cls.random_user = User.objects.create(username='Random user')
        cls.any_user = User.objects.create(username='Any user')

        cls.post = Post.objects.create(text='Test text', author=cls.author)
        Follow.objects.create(user=cls.any_user, author=cls.author)

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def tearDown(self) -> None:
        super().tearDown()
        Follow.objects.all().delete()

    def setUp(self) -> None:
        super().setUp()
        self.auth_client = Client()
        self.auth_client.force_login(self.main_user)

        self.auth_random_client = Client()
        self.auth_random_client.force_login(self.random_user)

    def test_auth_user_follow(self):
        '''Проверяем возможность подписаться на автора'''
        #  Определяем количество подписок на автора:
        start_follows_count = Follow.objects.filter(author=self.author).count()
        #  Подписываемся на автора:
        self.auth_client.get(reverse('posts:profile_follow',
                                     args=(self.author.username,)
                                     )
                             )
        #  Считаем количество записей в базе после подписки:
        next_follows_count = Follow.objects.filter(author=self.author).count()
        #  Проверяем, что количество записей выросло на 1:
        self.assertEqual(next_follows_count, start_follows_count + 1,
                         'Подписка на автора работает не так как ожидалось.')
        #  Проверяем, что в БД существует подписка с указанными
        #  при создании параметрами
        self.assertTrue(Follow.objects.filter(user=self.main_user,
                                              author=self.author
                                              ).exists()
                        )

    def test_unsubscribe(self):
        '''Проверка работоспособности функции "отписки от автора"'''
        #  Определяем общее количество подписок на автора:
        start_follows_count = Follow.objects.filter(author=self.author).count()

        #  Создаем подписку на автора от main_user:
        Follow.objects.create(user=self.main_user, author=self.author)

        #  Считаем количество записей в базе после подписки:
        next_follows_count = Follow.objects.filter(author=self.author).count()

        #  Проверяем, что количество записей выросло на 1:
        self.assertEqual(next_follows_count, start_follows_count + 1)

        #  Выполняем запрос на отписку от автора
        self.auth_client.get(reverse('posts:profile_unfollow',
                             args=(self.author.username,))
                             )
        #  Проверяем уменьшение количества подписок на 1:
        final_follows_count = Follow.objects.filter(author=self.author).count()
        self.assertEqual(final_follows_count, start_follows_count)

        #  Проверяем, что подписка с указанными параметрами отсутствует в БД
        self.assertFalse(Follow.objects.filter(user=self.main_user,
                                               author=self.author
                                               ).exists()
                         )

    def test_auth_post_exists(self):
        '''Проверка того, что пост автора отображается на странице фолловера'''
        #  Создаем подписку на автора
        Follow.objects.create(user=self.main_user, author=self.author)
        #  Создаем новый пост автора
        new_post = Post.objects.create(text='New post',
                                       author=self.author)
        #  Получаем контекст со страницы избранных постов
        response = self.auth_client.get(reverse('posts:follow_index'))
        context = response.context['posts']

        self.assertIn(Post.objects.filter(text=new_post.text)[0], context,
                                         ('Пост автора отсутствует в ленте '
                                          'фолловера'
                                          )
                      )

    def test_non_auth_post_absence(self):
        '''Проверка того, что пост автора не отображается на
        странице юзера, не подписанного на него.'''
        #  Создаем новый пост автора
        new_post = Post.objects.create(text='New post',
                                       author=self.author)

        #  Получаем контекст со страницы избранных постов
        response = self.auth_random_client.get(reverse('posts:follow_index'))
        context = response.context['posts']

        self.assertNotIn(Post.objects.filter(text=new_post.text)[0], context,
                                            ('Пост автора присутствует в ленте'
                                             ' не фолловера.'
                                             )
                         )
