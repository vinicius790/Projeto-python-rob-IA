from django.db import models
from django.core.exceptions import ValidationError

class Colaborador(models.Model):
    nome = models.CharField(max_length=100, verbose_name='Nome')
    cpf = models.CharField(max_length=11, unique=True, verbose_name='CPF')
    salario = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Salário')
    vale_refeicao = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Vale Refeição')

    def clean(self):
        super().clean()
        if not self.cpf.isdigit():
            raise ValidationError('O CPF deve conter apenas dígitos.')

    def __str__(self):
        return f"{self.nome} ({self.cpf})"

    class Meta:
        verbose_name = 'Colaborador'
        verbose_name_plural = 'Colaboradores'

class Pagamento(models.Model):
    colaborador = models.ForeignKey(Colaborador, on_delete=models.CASCADE, verbose_name='Colaborador')
    salario = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Salário')
    vale_refeicao = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Vale Refeição')
    data = models.DateField(verbose_name='Data')

    def __str__(self):
        return f"Pagamento de {self.salario} e {self.vale_refeicao} para {self.colaborador.nome}"

    class Meta:
        verbose_name = 'Pagamento'
        verbose_name_plural = 'Pagamentos'
        ordering = ['data']
