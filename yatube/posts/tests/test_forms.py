import shutil
import tempfile
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Group, Post, Comment

User = get_user_model()

TEST_IMAGE = (b'\x47\x49\x46\x38\x39\x61\x02\x00'
              b'\x01\x00\x80\x00\x00\x00\x00\x00'
              b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
              b'\x00\x00\x00\x2C\x00\x00\x00\x00'
              b'\x02\x00\x01\x00\x00\x02\x02\x0C'
              b'\x0A\x00\x3B'
              )

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class TestForm(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        cls.user = User.objects.create_user(username='Kirill')

        cls.group = Group.objects.create(
            title='Test title',
            description='Test description',
            slug='test-slug'
        )

        cls.image = SimpleUploadedFile(name='Test.gif',
                                       content=TEST_IMAGE,
                                       content_type='image/gif'
                                       )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self) -> None:
        super().setUp()

        self.post = Post.objects.create(text='Test text',
                                        author=self.user,
                                        group=self.group
                                        )

        self.client = Client()
        self.client.force_login(self.user)

        self.unauthorized_client = Client()

    def test_post_create_form(self):
        '''
        Проверка возможности создания поста
        через форму.
        '''
        posts_count = Post.objects.count()
        form = {
            'text': 'New post',
            'group': self.group.id,
            'image': self.image
        }

        self.client.post(reverse('posts:post_create'),
                         form,
                         follow=True
                         )
        latest_post = Post.objects.all().first()

        post_data = {
            latest_post.text: form['text'],
            latest_post.author: self.user,
            latest_post.group: self.group
        }

        image_db_name = f'posts/{self.image.name}'

        self.assertEqual(Post.objects.count(), posts_count + 1)

        for data, expected_value in post_data.items():
            with self.subTest(value=data):
                self.assertEqual(data, expected_value,
                                 f'Значение {data} не '
                                 'соответствует ожидаемому.'
                                 )
        self.assertTrue(Post.objects.filter(text=form['text'],
                                            image=image_db_name).exists()
                        )

    def test_not_auth_create_post(self):
        '''
        Проверка возможности создания поста
        неавторизованным пользователем.
        '''
        posts_count = Post.objects.count()

        form = {
            'text': 'New post',
            'group': self.group.id
        }

        response = self.unauthorized_client.post(reverse('posts:post_create'),
                                                 form,
                                                 follow=True)

        target_url = (f'{reverse("users:login")}?next='
                      f'{reverse("posts:post_create")}'
                      )

        self.assertEqual(Post.objects.all().count(),
                         posts_count)
        self.assertRedirects(response,
                             target_url,
                             status_code=HTTPStatus.FOUND,
                             target_status_code=HTTPStatus.OK)

    def test_post_edit_form(self):
        '''
        Проверка возможности редактирования поста.
        '''
        post_id = Post.objects.all().first().id
        new_text = 'Python is awesome'
        form = {
            'text': new_text,
            'group': self.group.id
        }

        self.client.post(reverse('posts:post_edit',
                                 kwargs={'post_id': post_id}
                                 ),
                         form,
                         follow=True
                         )
        updated_post = Post.objects.get(pk=post_id)
        updated_params = {
            updated_post.text: new_text,
            updated_post.author: self.user,
            updated_post.group: self.group
        }
        for param, value in updated_params.items():
            with self.subTest(field=param):
                self.assertEqual(param, value)

    def test_auth_user_comment(self):
        '''Тестирование возможнсти добавления комментария к посту
        авторизованным юзером.'''

        post = Post.objects.all().first()

        form = {
            'text': 'Test comment',
            'author': self.user,
            'post': post.id
        }

        #  Проверяем наличие поста в БД после отправки
        #  пост-запроса от авторизованного юзера:
        self.client.post(reverse('posts:add_comment',
                                 args=(post.id,)),
                         form,
                         follow=True
                         )
        self.assertTrue(Comment.objects.all())

    def test_for_non_auth_user(self):
        '''Тестирование взаимодействия с функционалом комментирования
        постов неавторизованным юзером'''

        post = Post.objects.all().first()

        form = {
            'text': 'Test comment',
            'author': self.user,
            'post': post.id
        }
        #  Выполняем пост-запрос для создания комментария к посту:
        response = self.unauthorized_client.post(reverse('posts:add_comment',
                                                         args=(post.id,)),
                                                 form,
                                                 follow=True
                                                 )
        #  Проверяем отсутствие комментов в БД после отправки
        #  пост-запроса от неавторизованного юзера:
        self.assertFalse(Comment.objects.filter(text=form['text']))

        #  Проверяем редирект неавторизованного юзера при попытке
        #  создать комментарий:
        target_url = (f'{reverse("users:login")}?next='
                      f'{reverse("posts:add_comment", args=(post.id,))}'
                      )
        self.assertRedirects(response,
                             target_url,
                             status_code=HTTPStatus.FOUND,
                             target_status_code=HTTPStatus.OK)
