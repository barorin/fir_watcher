from sqlalchemy import Column, Date, ForeignKey, String

from database import Base, engine


class Link(Base):
    __tablename__ = "links"

    firm_name = Column(String)
    country = Column(String)
    report_date = Column(Date)
    pdf_url = Column(String, primary_key=True)
    file_name = Column(String, unique=True)


class Report(Base):
    __tablename__ = "reports"

    issuer = Column(String)
    industry = Column(String)
    type_of_audit_and_related_area_affected = Column(String)
    description_of_the_deficiencies_identified = Column(String)
    file_name = Column(String, ForeignKey("links.file_name"))
    file_name_issuer = Column(String, primary_key=True)


if __name__ == "__main__":
    # テーブルの作成
    Base.metadata.create_all(bind=engine)
