from datetime import datetime
from sqlalchemy import select, insert, update, and_
from database import (DGazprom, DManual, DUser, DVisitedUser, DBaseStation,
                      DAllInfo, DAccident, DAddInfo, new_session)

class Repo:
    @classmethod
    async def select_pass(cls, login, psw, tg_id):
        """Authentication"""
        async with new_session() as session:
            q = select(DUser).where(DUser.login == login, DUser.password == psw,
                                    DUser.tg_id == str(tg_id))
            result = await session.execute(q)
            answer = result.scalar()
            return answer

    @classmethod
    async def select_accident(cls, status):
        """Select accident by status"""
        async with new_session() as session:
            if status == "open" or status == "check":
                q = select(DAccident).order_by(DAccident.id.desc()).where(DAccident.status == status)
            else:
                q = select(DAccident).order_by(DAccident.id.desc()).where(DAccident.status == status).limit(5)
            result = await session.execute(q)
            answer = result.scalars()
            await session.commit()
            return answer

    @classmethod
    async def select_accident_number(cls, number):
        """Select accident by number"""
        async with new_session() as session:
            number = str(number)
            query = select(DAccident).where(DAccident.number == number)
            result = await session.execute(query)
            answer = result.scalar()
            await session.commit()
            return answer

    @classmethod
    async def select_azs(cls, number):
        """Select AZS"""
        async with new_session() as session:
            number = str(number)
            q = select(DGazprom).where(DGazprom.number == number)
            result = await session.execute(q)
            answer = result.scalar()
            return answer

    @classmethod
    async def select_manual(cls, ssid):
        """Select manual"""
        async with new_session() as session:
            q = select(DManual).where(DManual.id == int(ssid))
            result = await session.execute(q)
            answer = result.scalar()
            return answer

    @classmethod
    async def insert_into_visited_date(cls, login, action):
        """Insert visited users"""
        async with new_session() as session:
            date_created = datetime.now()
            q = DVisitedUser(login=login, date_created=date_created, action=action)
            session.add(q)
            await session.commit()
            return

    @classmethod
    async def select_action(cls, number):
        """View visited users"""
        async with new_session() as session:
            query = select(DVisitedUser).order_by(DVisitedUser.id.desc()).limit(int(number))
            result = await session.execute(query)
            answer = result.scalars().all()
            return answer

    @classmethod
    async def select_bs_number(cls, number):
        """Select BS by number"""
        async with new_session() as session:
            query = select(DBaseStation).where(DBaseStation.number == int(number))
            result = await session.execute(query)
            answer = result.scalar()
            await session.commit()
            return answer

    @classmethod
    async def select_bs_address(cls, address):
        """Select BS by street"""
        async with new_session() as session:
            query = select(DBaseStation).where(DBaseStation.address.like(f"%{address}%"))
            result = await session.execute(query)
            answer = result.scalars()
            await session.commit()
            return answer

    @classmethod
    async def select_all_info(cls, temp):
        """Select info fttx"""
        async with new_session() as session:
            result = temp.split(", ")
            city = str(result[0])
            street = str(result[1])
            number = str(result[2])
            query = select(DAllInfo).where(DAllInfo.city == city,
                                           DAllInfo.street == street,
                                           DAllInfo.number == number)
            result = await session.execute(query)
            answer = result.scalar()
            await session.commit()
            return answer

    @classmethod
    async def select_stat(cls):
        """Select stat visited"""
        async with new_session() as session:
            q = select(DVisitedUser).order_by(DVisitedUser.id.desc()).limit(5)
            result = await session.execute(q)
            answer = result.scalars().all()
            return answer

    @classmethod
    async def insert_info(cls, info):
        """insert new info in fttx_fttx"""
        async with new_session() as session:
            reestr = int(info[0])
            date = datetime.now()
            city = info[1]
            street = info[2]
            home = info[3]
            apartment = info[4]
            name = info[5]
            cable_1 = int(info[6])
            cable_2 = int(info[7])
            cable_3 = int(info[8])
            connector = int(info[9])
            query = await session.execute(insert(DAddInfo).values(reestr=reestr, date_created=date, city=city,
                                                                  street=street, home=home, apartment=apartment,
                                                                  name=name, cable_1=cable_1, cable_2=cable_2,
                                                                  cable_3=cable_3, connector=connector
                                                                  ))
            await session.commit()
            await session.close()
            return query

    @classmethod
    async def update_accident(cls, l):
        """Update accident by number"""
        async with new_session() as session:
            number = str(l[0])
            decide = str(l[2])
            status = str(l[1])
            q = (
                update(DAccident).where(DAccident.number == number).values(decide=decide, status=status)
            )
            answer = await session.execute(q)
            await session.commit()
            return answer

    @classmethod
    async def grafik_ring(cls, start_date, end_date):
        """Select date for graph"""
        async with new_session() as session:
            query = select(DAddInfo).where(
                DAddInfo.date_created.between(start_date, end_date)
            )
            result = await session.execute(query)
            answer = result.scalars().all()
            await session.commit()
            return answer

    @classmethod
    async def exit_user_bot(cls, tg_id):
        """Exit."""
        async with new_session() as session:
            q = select(DUser).where(and_(DUser.tg_id == str(tg_id)))
            result = await session.execute(q)
            answer = result.scalars().first()
            if answer is None:
                return None
            answer.active = 0
            await session.commit()
            return answer
