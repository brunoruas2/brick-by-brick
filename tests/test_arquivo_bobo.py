from brick_by_brick.arquivo_bobo import funcao_boba


def test_deve_retornar_o_valor_do_paramentro():
    valor = 10  # Arrange

    resposta = funcao_boba(valor)  # Act

    assert resposta == valor  # Assert
