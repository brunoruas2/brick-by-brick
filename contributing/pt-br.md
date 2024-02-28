# Como contribuir no desenvolvimento

## Desenvolvendo
Após ter clonado o repositório, aqui estão algumas orientações para configurar o seu ambiente

1. Tenha um editor de texto da sua preferência
2. Um terminal a sua escolha
3. A versão 3.11 do Python instalada
    - Pode baixar no [site oficial](https://www.python.org/downloads/)
    - Ou via [pyenv](https://github.com/pyenv/pyenv)
4. O [Poetry](https://python-poetry.org/) para gerenciar os pacotes e o seu ambiente
virtual evitando problemas com outros projetos da sua maquina
5. O [Git](https://git-scm.com/) para gerenciar versões

### Ambiente virtual com `venv`
Para fazer a instalação do python 3.11 no seu ambiente virtual é **reconmendado**
que se use o [pyenv](https://github.com/pyenv/pyenv).

Caso encontre dificuldades durante a instalação, o pyenv conta com dois assistentes 
simplificados para sua configuração. Para windows, use o [pyenv-windows](https://pyenv-win.github.io/pyenv-win/).
Para GNU/Linux e MacOS, use o [pyenv-installer](https://github.com/pyenv/pyenv-installer).

Navegue até o diretório onde fará os exercícios e irá executar os códigos de exemplo 
no seu terminal e digite os seguintes comandos no seu terminal:

```bash
$ pyenv update
$ pyenv install 3.11.8
```
###### Certifique a versão 3.11 esteja instalada

```bash
$ pyenv versions
* system (set by /home/azevedo/.pyenv/version)
  3.11.8
```
A resposta esperada é que o `Python 3.11` esteja nessa lista.

### Gerenciamento de Dependências com o Poetry
Após instalar o Python o próximo passo é instalar o [Poetry](https://python-poetry.org/),
um gerenciador de pacotes e dependências para Python. O poetry facilita a criação,
o gerenciamento e a distribuição de pacotes Python.

Vou deixar de recomendação um vídeo caso queria aprender mais sobre a ferramenta
[Live de Python](https://www.youtube.com/watch?v=ZOSWdktsKf0&t=1s)

Para instalar o Poetry você deve seguir a seguinte instrução.
```bash
pip install poetry
```

### Instalação das Dependências
Agora inicializaremos nosso ambiente virtual com o Poetry e instalaremos as dependências
necessárias.
```bash
$ poetry install
```
Para habilitarmos nosso ambiente virtual, para que o python consiga enxergar nossas
dependências instaladas. O poetry tem um comando específico para isso:
```bash 
$ poetry shell
```
Dessa forma o ambiente sincroniza a versão do python através do arquivo `.python-version`
e utiliza as versões das biblioetcas de acordo com o versionamento do arquivo
`pyproject.toml`.

### Ferramentas de Desenvolvimento
#### Ruff
[Ruff](https://docs.astral.sh/ruff/) é um analisador estático de códifo. A função
dele é verificar se estamos programando de acordo com boas práticas do python.

#### Isort
[isort](https://pycqa.github.io/isort/) é uma ferramenta parar organizar os imports.
Na PEP-8 existe uma regra de [precedência sobre os imports](https://peps.python.org/pep-0008/#imports).
A funçao do isrot é agrupar os imports e também ordená-los em ordem alfabética,
para ajudar a buscar onde e o que foi importado.

#### Pytest
[Pytest](https://docs.pytest.org/en/8.0.x/) é um framework de teste, que usaremos 
para escrever e executar nossos testes.

#### Blue
[Blue](https://blue.readthedocs.io/en/latest/index.html#) é um formatador de código.
A ideia por trás do uso de um formatador é simplesmente padronizar toda a escrita 
do código. Como, por exemplo, definimos strings entre ' ou entre "? Quando a 
linha exceder a 79 caracteres, como faremos a quebra de linha? Se quebrarmos a 
linha, usaremos vírgula no último valor ou não? Com o foco de padronizar o código.

#### Taskipy
[Taskipy](https://github.com/taskipy/taskipy) é um executor de tarefas (*task runner*)
auxilador em nossa aplicação. Para evitar de lembrar comandos nos conseguimos
substituir por algo mais simples como `task test` e executará nossa rotina de testes.

##### Os principais comandos disponíveis
```bash
$ task lint
```
Essa tarefa é responsável por nos mostrar se nossa formatação esta condizente com
a PEP-8, mostrando o deve ser feito de diferente caso não esteja na formatação
adequada.

---

```bash
$ task format
```
Essa tarefa é responsável por fazer a formatação automática caso você não queria
entender o que aconteceu de errado com o seu código e porque ele não se adequa
em uma das regras de boas práticas.

---

```bash
$ task test
```
Essa tarefa é responsável por rodar nossos testes presentes no diretório `teste`
e também nas `docstrings` ela mostra uma tabela que nos da dados muito valiosos
como a quantidade de linhas no nosso código (Stmts), temos uma coluna de `Miss`
que representa quantas linhas não foram executadas e por último a coluna `Coverage`
que representa a razão entre as duas outras colunas.

Podemos observar melhor nosso coverage através do arquivo `htmlcov/index.html`.
abrindo esse arquivo no browser de sua preferência, como por exemplo:

```bash
firefox htmlcov/index.html
```

### Estrutura de um teste
Para escrever testes, eu gosto da abordagem [AAA](https://xp123.com/articles/3a-arrange-act-assert/)
que divide o teste em três etapas: Arrange, Act, Assert.

#### Fase 1 - Arrange (Organizar)
Nessa etapa a gente prepara o ambiente para o teste, declarando variáveis que serão
usadas na nossa função para o teste.

#### Fase 2 - Act (Agir)
Nessa etapa é onde acontece a ação principal onde nossa função a ser testada será
usada com as variáveis que predefinimos anteriormente e guardaremos a resposta.

#### Fase 3 - Assert (Afirmar)
Nessa ultima etapa é responsável por verificar se tudo ocorreu como esperado, onde
nossa variável que saiu da função está retornado o valor esperado.

