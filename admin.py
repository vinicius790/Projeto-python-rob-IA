from django.contrib import admin
from .models import Colaborador, Pagamento

@admin.register(Colaborador)
class ColaboradorAdmin(admin.ModelAdmin):
    list_display = ('nome', 'cpf', 'salario', 'vale_refeicao')
    search_fields = ('nome', 'cpf')

@admin.register(Pagamento)
class PagamentoAdmin(admin.ModelAdmin):
    list_display = ('colaborador', 'salario', 'vale_refeicao', 'data')
    list_filter = ('data',)
    search_fields = ('colaborador__nome',)
