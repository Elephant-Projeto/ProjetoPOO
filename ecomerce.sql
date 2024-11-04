
CREATE DATABASE IF NOT EXISTS ecomerce;
USE ecomerce;


CREATE TABLE CLIENTE (
    ID_CLIENTE INTEGER PRIMARY KEY AUTO_INCREMENT, 
    NOME VARCHAR(255) NOT NULL,
    EMAIL VARCHAR(255) NOT NULL,
    TELEFONE VARCHAR(20),
    CPF VARCHAR(14) UNIQUE NOT NULL,
    SENHA VARCHAR(255) UNIQUE NOT NULL
);


CREATE TABLE ENDERECO (
    CEP VARCHAR(10) NOT NULL,
    RUA VARCHAR(255) NOT NULL,
    BAIRRO VARCHAR(255) NOT NULL,
    NUMERO_CASA INTEGER NOT NULL,
    CLIENT_ID INTEGER,
    FOREIGN KEY (CLIENT_ID) REFERENCES CLIENTE(ID_CLIENTE)
);


CREATE TABLE PRODUTO (
    ID_PRODUTO INTEGER PRIMARY KEY AUTO_INCREMENT, 
    VALOR_PROD FLOAT NOT NULL, 
    QTD_ESTOQUE INTEGER NOT NULL,
    COR VARCHAR(50),
    TAMANHO VARCHAR(50),
    MARCA VARCHAR(100),
    IMAGEM LONGBLOB,
    TIPO_TECIDO VARCHAR(100)
);

CREATE TABLE PEDIDO (
    ID_COMPRA INTEGER PRIMARY KEY AUTO_INCREMENT, 
    PRODUTO_ID INTEGER,
    CLIENTE_ID INTEGER,
    QTD_PEDIDO INTEGER,
    FORMA_PAGAMENTO VARCHAR(50), 
    STATUS_PAGAMENTO VARCHAR(50), 
    FOREIGN KEY (PRODUTO_ID) REFERENCES PRODUTO(ID_PRODUTO),
    FOREIGN KEY (CLIENTE_ID) REFERENCES CLIENTE(ID_CLIENTE)
);



CREATE TABLE FEEDBACK (
    CLI_ID INTEGER,
    PROD_ID INTEGER,
    DESCRICAO_AVALIA TEXT, 
    FK_CLIENTE_SENHA VARCHAR(255),
    FOREIGN KEY (CLI_ID) REFERENCES CLIENTE(ID_CLIENTE),
    FOREIGN KEY (PROD_ID) REFERENCES PRODUTO(ID_PRODUTO)
);


CREATE TABLE TELEFONE (
    C_ID INTEGER PRIMARY KEY AUTO_INCREMENT,
    TELEFONE VARCHAR(20),
    CELULAR VARCHAR(20),
    FOREIGN KEY (C_ID) REFERENCES CLIENTE(ID_CLIENTE)
);