    async def fetch_latest_founds(self, ctx: commands.Context, timestamp=None) -> list:
        """
        Queue a request to the nationstates API to get the latest nation foundings from the happenings shard.
        Then parse it to get the names from the text attribute, and return the names as a list.
        :param timestamp:
        """
        if timestamp is None:
            vals = await self.bot.queue(
                str(uuid4()),
                f"https://www.nationstates.net/cgi-bin/api.cgi?q=happenings;filter=founding",
                "get",
                ctx,
            )
        else:
            vals = await self.bot.queue(
                str(uuid4()),
                f"https://www.nationstates.net/cgi-bin/api.cgi?q=happenings;filter=founding;sincetime={timestamp}",
                "get",
                ctx,
            )

        if vals["status"] != "success":
            raise Exception(f"Failed to fetch latest foundings: {vals['status']}")

        targets = []

        root = ET.fromstring(vals["response"])
        happenings = root.find("HAPPENINGS")
        events = happenings.findall("EVENT")
        event_counter = 0
        for event in events:
            text = event.find("TEXT").text
            name = text.strip("@@").split("@@")
            can_recruit = True
            for pattern in self.filter_list:
                if pattern in name[0] or name[0] in pattern:
                    can_recruit = False
                    break
            if can_recruit:
                if name[0] not in self.sent_during_session:
                    targets.append(name[0])
                    self.sent_during_session.add(name[0])
                    event_counter += 1
            if event_counter >= 8:
                break
            else:
                continue
        return targets
      
@commands.command()
async def recruit(self, ctx: commands.Context):
    """
    Starts a recruitment session.
    """
    if self.ongoing_session:
        await ctx.send(
            "A recruitment session is already ongoing. Type `JOIN` to join."
        )

    else:
        self.ongoing_session = True
        self.active_recruiters.append(ctx.author)
        await ctx.send("A recruitment session has started")
        while True:
            if self.ongoing_session:
                if self.session_just_started is True:
                    targets = await self.fetch_latest_founds(ctx)
                    print("Targets:", targets)
                    self.session_just_started = False
                else:
                    targets = await self.fetch_latest_founds(
                        timestamp=self.timestamp,
                        ctx=ctx
                    )
                if len(targets) > 0:
                    self.timestamp = time()
                    buttons = []
                    templates = {}
                    for recruiter in self.active_recruiters:
                        async with self.bot.pool.acquire() as conn:
                            vals = await conn.fetch(
                                "SELECT template FROM telegram_templates WHERE userid = $1 AND active = $2",
                                recruiter.id,
                                True,
                            )
                            for row in vals:
                                if row["template"] is not None:
                                    link = Button(
                                        label=f"{recruiter.name}",
                                        style=ButtonStyle.url,
                                        url="https://nationstates.net/page=compose_telegram",
                                    )
                                    for target in targets:
                                        await conn.execute(
                                            "INSERT INTO telegrams_sent (userid, target_id, template) VALUES ($1, $2, $3)",
                                            recruiter.id,
                                            target,
                                            row["template"],
                                        )
                                    buttons.append(link)
                                    templates[recruiter.id] = row["template"]
                            vals = await conn.fetch(
                                "SELECT * FROM recruitment_tally WHERE userid = $1",
                                recruiter.id,
                            )
                            if len(vals) == 0:
                                await conn.execute(
                                    "INSERT INTO recruitment_tally (userid, numsent) VALUES ($1, $2)",
                                    recruiter.id,
                                    len(targets),
                                )
                            else:
                                await conn.execute(
                                    "UPDATE recruitment_tally SET numsent = numsent + $1 WHERE userid = $2",
                                    len(targets),
                                    recruiter.id,
                                )

                    await ctx.send(
                        f"{', '.join([rec.mention for rec in self.active_recruiters])}\n**Targets:**\n{', '.join(targets)}",
                        components=MessageComponents.add_buttons_with_rows(
                            *buttons
                        ),
                    )
                    tem_mens = []
                    for key, value in templates.items():
                        rec = [rec for rec in self.active_recruiters if rec.id == key][0]
                        string = f"{rec.mention}: {value}"
                        tem_mens.append(string)
                    newline = "\n"
                    await ctx.send(
                        f"{newline.join(tem_mens)}"
                    )
                    await ctx.send(
                        "Copy and paste the template and targets into the compose telegram page and send it to "
                        "the target nation. "
                    )

                    if len(targets) > 6:
                        await asyncio.sleep(len(targets) * 20)
                    else:
                        await asyncio.sleep(120)
                else:
                    await asyncio.sleep(10)
            else:
                break
