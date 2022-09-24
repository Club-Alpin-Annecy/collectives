""" Module for all Event relationship to others model objects"""


from sqlalchemy.ext.declarative import declared_attr

from collectives.models.globals import db


class RelationshipUser:
    """Part of User class for model relationships.

    Not meant to be used alone."""

    # For relationship Mixin, we have to use a function and declared_attr, but it is the same as
    # declaring an attribute. Cf
    # https://docs.sqlalchemy.org/en/13/orm/extensions/declarative/mixins.html#mixing-in-columns
    @declared_attr
    def roles(self):
        """List of granted roles within this site for this user. (eg administrator)

        :type: list(:py:class:`collectives.models.role.Role`)"""
        return db.relationship("Role", backref="user", lazy=True)

    @declared_attr
    def registrations(self):
        """List registration of the user.

        :type: list(:py:class:`collectives.models.registration.Registration`)
        """
        return db.relationship("Registration", backref="user", lazy=True)

    @declared_attr
    def reservations(self):
        """List of reservations made by the user.

        :type: list(:py:class:`collectives.models.reservation.Reservation`)
        """
        return db.relationship(
            "Reservation",
            back_populates="user",
        )

    @declared_attr
    def payments(self):
        """List of payments made by the user.

        :type: list(:py:class:`collectives.models.payment.Payment`)
        """
        return db.relationship(
            "Payment", backref="buyer", foreign_keys="[Payment.buyer_id]", lazy=True
        )

    @declared_attr
    def reported_payments(self):
        """List of payments reported by the user (that is, manually entered by the user).

        :type: list(:py:class:`collectives.models.payment.Payment`)
        """
        return db.relationship(
            "Payment",
            backref="reporter",
            foreign_keys="[Payment.reporter_id]",
            lazy=True,
        )
