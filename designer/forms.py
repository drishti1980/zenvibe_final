from django import forms

from .models import BlogComment


class BlogCommentForm(forms.ModelForm):

    class Meta:
        model = BlogComment

        fields = [
            "name",
            "email",
            "website",
            "comment",
        ]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "zv-comment-input",
                    "placeholder": "Your name",
                    "autocomplete": "name",
                }
            ),

            "email": forms.EmailInput(
                attrs={
                    "class": "zv-comment-input",
                    "placeholder": "Your email",
                    "autocomplete": "email",
                }
            ),

            "website": forms.URLInput(
                attrs={
                    "class": "zv-comment-input",
                    "placeholder": "Website (optional)",
                    "autocomplete": "url",
                }
            ),

            "comment": forms.Textarea(
                attrs={
                    "class": "zv-comment-textarea",
                    "placeholder": "Write your comment...",
                    "rows": 7,
                }
            ),
        }

    def clean_name(self):
        return self.cleaned_data["name"].strip()

    def clean_comment(self):
        comment = self.cleaned_data["comment"].strip()

        if len(comment) < 3:
            raise forms.ValidationError(
                "Please enter a longer comment."
            )

        return comment