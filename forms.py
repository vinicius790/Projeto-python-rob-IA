from django import forms
from .models import Robo, Sensor, Atuador

class RoboForm(forms.ModelForm):
    class Meta:
        model = Robo
        fields = ['nome', 'velocidade_atual', 'angulo_atual', 'modo_operacao', 'sensores', 'atuadores']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['sensores'].widget = forms.SelectMultiple(choices=Sensor.objects.all().values_list('id', 'nome'))
        self.fields['atuadores'].widget = forms.SelectMultiple(choices=Atuador.objects.all().values_list('id', 'nome'))

    def clean_velocidade_atual(self):
        """Valida a velocidade atual do robô."""
        velocidade = self.cleaned_data['velocidade_atual']
        velocidade_maxima = self.instance.velocidade_maxima
        if velocidade > velocidade_maxima:
            raise forms.ValidationError(f"A velocidade deve ser menor ou igual a {velocidade_maxima}.")
        return velocidade

    def clean_angulo_atual(self):
        """Valida o ângulo atual do robô."""
        angulo = self.cleaned_data['angulo_atual']
        angulo_maximo = self.instance.angulo_maximo
        if angulo > angulo_maximo or angulo < -angulo_maximo:
            raise forms.ValidationError(f"O ângulo deve estar entre -{angulo_maximo} e {angulo_maximo} graus.")
        return angulo

    def clean(self):
        """Validações que envolvem múltiplos campos."""
        cleaned_data = super().clean()
        modo_operacao = cleaned_data.get('modo_operacao')
        sensores = cleaned_data.get('sensores')
        atuadores = cleaned_data.get('atuadores')

        # Verificar se a combinação de modo de operação, sensores e atuadores é válida
        # ... lógica de validação ...

        return cleaned_data
