# LINEBot-sujata
LINE boot awards2018に応募する作品


# PostgreSQL command
- CREATE TABLE Users(
	UserId character(33),
	name varchar(20),
	zipcode char(7),
	serve decimal,
	receive decimal,
	star decimal
);

- Create table servers (
	UserId character(33),
	at time
);

- Create table receivers (
	userId character(33),
	at time
);
