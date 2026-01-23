from django import forms
from .models import Post

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['content', 'pinned']  # убрали visibility_groups
        widgets = {
            'content': forms.Textarea(attrs={'rows': 5, 'class': 'w-full border rounded-lg p-3'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user and not user.is_staff:
            self.fields.pop('pinned')  # обычные пользователи не могут закреплять