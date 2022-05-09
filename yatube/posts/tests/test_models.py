from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Group, Post

User = get_user_model()


class TestPostModel(TestCase):
    '''
    Тестирование модуля models приложения 'posts'.
    '''
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовое название группы',
            description='Тестовое описание группы',
            slug='test-slug'
        )
        cls.post = Post.objects.create(
            text='Текст поста для теста',
            author=cls.user
        )

    def test_models_have_correct_object_names(self):
        '''
        Проверка того, что метод __str__ правильно отображается
        в объектах моделей.
        '''
        group_str = 'Тестовое название группы'
        post_text = 'Текст поста для теста'
        post_str = post_text[:15]

        self.assertEqual(self.group.__str__(),
                         group_str,
                         'Метод "__str__" для модели '
                         'Group отображается неверно'
                         )

        self.assertEqual(self.post.__str__(),
                         post_str,
                         'Метод "__str__" для модели '
                         'Post отображается неверно'
                         )

    def test_models_verbose_names(self):
        '''
        Тестирование корректного отображения verbose_names
        в полях моделей.
        '''
        group_fields_verbose_names = {
            'title': 'Название группы',
            'description': 'Описание группы'
        }

        post_fields_verbose_names = {
            'text': 'Текст поста',
            'author': 'Автор',
            'pub_date': 'Дата публиации'
        }

        for field, verbose_name in group_fields_verbose_names.items():
            with self.subTest(field=field):
                self.assertEqual(
                    self.group._meta.get_field(field).verbose_name,
                    verbose_name,
                    f'verbose_name поля {field} '
                    'не соответствует ожидаемому.'
                )

        for field, verbose_name in post_fields_verbose_names.items():
            with self.subTest(field=field):
                self.assertEqual(self.post._meta.get_field(field).verbose_name,
                                 verbose_name,
                                 f'verbose_name поля {field} '
                                 'не соответствует ожидаемому.'
                                 )

    def test_models_help_texts(self):
        '''
        Тестирование корректного отображения help_text
        в полях моделей.
        '''
        self.assertEqual(self.post._meta.get_field('text').help_text,
                         'Напишите текст поста',
                         'help_text для поля text модели '
                         'Post отображается неверно.'
                         )

        self.assertEqual(self.group._meta.get_field('description').help_text,
                         'Укажите описание',
                         'help_text для поля text модели '
                         'Post отображается неверно.'
                         )
