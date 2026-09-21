# Commercial Messages: Consent and Opt-Out

A commercial message (a promotion, a newsletter, a birthday discount, a
"come back" nudge, a welcome carrying an offer) goes only to a person whose
**current** consent covers that channel, and always carries a working way out.
A transactional message about something the person ordered or booked
(confirmation, reminder, cancellation, receipt, password reset) needs neither.

Legal anchors: GDPR art. 7(3) (withdrawing must be as easy as giving),
ePrivacy Directive 2002/58/EC art. 13 (unsolicited e-mail and SMS need prior
consent) and its national implementations, RFC 2369 / RFC 8058 (one-click
unsubscribe), CAN-SPAM (an opt-out must keep working at least 30 days after
sending).

## Design

1. **Classify every message type in code**, in one place, with no default:
   ```python
   from enum import Enum

   class MessageKind(Enum):
       BOOKING_CONFIRMED = "BOOKING_CONFIRMED"
       BOOKING_REMINDER = "BOOKING_REMINDER"
       BIRTHDAY = "BIRTHDAY"
       WIN_BACK = "WIN_BACK"

       @property
       def is_commercial(self) -> bool:
           match self:
               case MessageKind.BIRTHDAY | MessageKind.WIN_BACK:
                   return True
               case MessageKind.BOOKING_CONFIRMED | MessageKind.BOOKING_REMINDER:
                   return False
           raise AssertionError(f"unclassified message kind {self}")
   ```
   A test pins both sets, so a new kind cannot ship until someone decides.
2. **One choke point** every sender passes through (automation dispatcher,
   bulk send). For a commercial kind it:
   - refuses to run without the recipient's person id (a coding error, so
     raise, never send bare);
   - re-checks consent right before sending, per person and channel. The
     audience was picked earlier; a withdrawal recorded since must still stop it;
   - appends the opt-out.
3. **Consent is a ledger**, append-only: grant, decline, revoke rows. "Has
   consent" is the newest row per (person, channel), with a deterministic
   tiebreak (`created_at DESC, id DESC`). E-mail and SMS are separate consents;
   one never authorizes the other.
4. **The opt-out:**
   - E-mail: a footer link inside the body, plus `List-Unsubscribe: <https://...>`
     and `List-Unsubscribe-Post: List-Unsubscribe=One-Click` headers.
   - SMS: a short link line. An alphanumeric sender cannot receive a "STOP"
     reply, so STOP alone is not a way out.
   - Per person and channel, in the message's language, landing on a page that
     withdraws without logging in.
   - The link token is stored hashed (see `secrets-at-rest.md`) and keyed by a
     secret of its own. Rotating the app secret must not kill links already sent.
   - Keep the link working at least 30 days after the latest message that
     carried it; a sliding expiry is fine.
5. **One address is one person** for sending: a blast goes once per address,
   and a withdrawal through a shared address revokes that channel for every
   record behind it.
6. **Log what was sent**, link included, so a retry replays the same body.

## Tests that prove it

- A person without consent on the channel gets nothing, even if they are in
  the audience source.
- E-mail consent does not produce an SMS.
- A withdrawal recorded after the audience was selected stops the send.
- A commercial kind dispatched without a person id raises.
- The sent body (and, for e-mail, the headers) carries that person's link.
- Transactional kinds still send to someone who refused marketing.

## Gotchas

- The link adds characters: an SMS can cross into a second segment. Count the
  body plus the opt-out line in the editor's length counter.
- A welcome message "just saying hello" becomes commercial the moment the
  template carries an offer. Classify by what the default template says, and
  be strict: when in doubt, it is commercial.
- Custom recipient lists typed in by staff are nobody's marketing consent.
  Either treat them as transactional one-offs with an explicit reason, or
  refuse commercial content to them.
