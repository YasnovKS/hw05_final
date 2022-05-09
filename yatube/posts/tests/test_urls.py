from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.core.cache import cache

from ..models import Group, Post

User = get_user_model()


class TestPostsUrls(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        '''
        Создаем фикстуры для тестирования:
        - два юзера (один будет авторизован, другой - нет),
        - два поста (один от авторизованного юзера, другой от
        постороннего),
        - два клиента (один с последующей авторизацией, другой - нет),
        - один объект группы для тестирования.
        '''
        super().setUpClass()

        cls.user = User.objects.create(username='Kirill')
        cls.other_user = User.objects.create(username='Other')

        Group.objects.create(
            title='Тестовое название',
            description='Тестовое описание',
            slug='test-slug'
        )

        cls.post = Post.objects.create(
            text='Тестовая запись',
            author=cls.user
        )
        cls.second_post = Post.objects.create(
            text='Пост постороннего автора',
            author=cls.other_user
        )

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        cache.delete('index_page')

    def setUp(self) -> None:
        super().setUp()

        self.non_auth_client = Client()

        self.auth_client = Client()
        self.auth_client.force_login(self.user)

    def test_page_status_unauthorized(self):
        '''
        Тестирование URL, доступных неавторизованному клиенту.
        '''
        testing_urls = {
            'index': reverse('posts:index'),
            'group/<slug>/': reverse('posts:group_list',
                                     args=[Group.objects.all().first().slug]
                                     ),
            'profile/<username>/': reverse('posts:profile',
                                           args=[self.user.username]
                                           ),
            'posts/<post_id>/': reverse('posts:post_detail',
                                        args=[self.post.id]
                                        )
        }
        for url, adress in testing_urls.items():
            with self.subTest(field=url):
                response = self.non_auth_client.get(adress)
                self.assertEqual(response.status_code,
                                 HTTPStatus.OK,
                                 f'Ошибка при переходе на страницу "{url}". '
                                 'Проверьте view-функцию.'
                                 )

    def test_templates_unauthorized(self):
        '''
        Проверка шаблонов, загружаемых из словаря templates,
        для страниц, доступных неавторизованному клиенту.
        '''
        templates = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list',
                    args=[Group.objects.all().first().slug]
                    ): 'posts/group_list.html',
            reverse('posts:profile',
                    args=[self.user.username]
                    ): 'posts/profile.html',
            reverse('posts:post_detail',
                    args=[self.post.id]
                    ): 'posts/post_detail.html'
        }
        for url, template in templates.items():
            with self.subTest(field=url):
                response = self.non_auth_client.get(url)
                self.assertTemplateUsed(response,
                                        template,
                                        'Некорректный шаблон'
                                        f' для страницы {url}.'
                                        )

    def test_create_page(self):
        '''
        Тестирование работы страницы создания поста для
        авторизованного и неавторизованного клиентов.
        '''
        auth_response = self.auth_client.get(reverse('posts:post_create'))

        non_auth_response = (self
                             .non_auth_client
                             .get(reverse('posts:post_create'),
                                  follow=True
                                  )
                             )

        self.assertEqual(auth_response.status_code,
                         HTTPStatus.OK,
                         'Переход на страницу создания '
                         'нового поста работает некорректно, '
                         'проверьте view-функцию.'
                         )
        self.assertTemplateUsed(auth_response,
                                'posts/create_post.html',
                                'Для страницы создания поста '
                                'используется некорректный шаблон.')
        self.assertRedirects(non_auth_response,
                             (f'{reverse("users:login")}?next='
                              f'{reverse("posts:post_create")}'
                              ),
                             status_code=HTTPStatus.FOUND,
                             target_status_code=HTTPStatus.OK,
                             msg_prefix=('Перенаправление неавторизованного '
                                         'пользователя со страницы /create/ '
                                         'работает некорректно.'),
                             fetch_redirect_response=False
                             )

    def test_post_edit(self):
        '''
        Тестирование возможности редактирования поста автором и посторонним
        юзером.
        '''
        post_response = self.auth_client.get(reverse('posts:post_edit',
                                                     args=[self.post.id]))
        self.assertEqual(post_response.status_code,
                         HTTPStatus.OK,
                         'Страница редактирования поста '
                         'работает некорректно'
                         )
        second_post_response = (self.auth_client
                                .get(reverse('posts:post_edit',
                                     args=[self.second_post.id])
                                     )
                                )

        target_url = reverse("posts:post_detail", args=[self.second_post.id])
        first_url = reverse("posts:post_edit", args=[self.second_post.id])

        self.assertRedirects(second_post_response,
                             f'{target_url}?next{first_url}',
                             status_code=HTTPStatus.FOUND,
                             target_status_code=HTTPStatus.OK,
                             msg_prefix=('Перенаправление пользователя '
                                         'со страницы редактирования '
                                         'поста работает некорректно.'),
                             fetch_redirect_response=False
                             )
        self.assertTemplateUsed(post_response,
                                'posts/create_post.html',
                                'Для страницы редактирования поста '
                                'применен некорректный шаблон.'
                                )

    def test_unexpected_page(self):
        '''
        Тестирование страницы с неизвестным URL.
        '''
        response = self.client.get('/unexisting_page/')
        self.assertEqual(response.status_code,
                         HTTPStatus.NOT_FOUND)
        self.assertTemplateUsed(response, 'core/404.html')

    def test_follow_urls(self):
        '''Тестирование urls, добавленных для реализации функции
        подписок на авторов.'''

        #  Проверка переадресации неавторизованного пользователя
        #  при попытке подписаться на автора, отписаться от него,
        #  оставить коммент на странице поста или загрузить страницу
        #  постов избранных авторов.
        follow_urls = {
            'follow_author': f'/profile/{self.user.username}/follow/',
            'unfollow_author': f'/profile/{self.user.username}/unfollow/',
            'create_comment': f'/posts/{self.post.id}/comment/',
            'follow_index': '/follow/'
        }
        for name, url in follow_urls.items():
            with self.subTest(name=name):
                target_url = (f'{reverse("users:login")}?next='
                              f'{url}'
                              )
                response = self.non_auth_client.get(url)
                self.assertRedirects(response,
                                     target_url,
                                     status_code=HTTPStatus.FOUND,
                                     target_status_code=HTTPStatus.OK)

        #  Проверим, что при запросе вышеуказанных страниц авторизованным
        #  пользователем, редирект происходит на ожидаемые страницы...
        success_urls = {
            f'/profile/{self.user.username}/follow/':
            reverse('posts:profile',
                    args=(self.user.username,)),
            f'/profile/{self.user.username}/unfollow/':
            reverse('posts:profile',
                    args=(self.user.username,)),
            f'/posts/{self.post.id}/comment/': reverse('posts:post_detail',
                                                       args=(self.post.id,))
        }
        for url, target in success_urls.items():
            with self.subTest(url=url):
                target_url = f'{target}?next{url}'
                response = self.auth_client.get(url)
                self.assertRedirects(response,
                                     target_url,
                                     status_code=HTTPStatus.FOUND,
                                     target_status_code=HTTPStatus.OK)

        #  ...а код страницы /follow/ при ответе на запрос от авторизованного
        #  пользователя равен 200
        response = self.auth_client.get('/follow/')
        self.assertEqual(response.status_code, HTTPStatus.OK)
