class GuildLimiter:
# Name of the class is a holdover from a previous version of this limiter code and has been retained to prevent having to change
# code in other locations that I really don't want to have to track down.

    def __init__(self, limit, per, logger: logging.Logger, pool: asyncpg.Pool):
        self.limit = limit
        self.per = per
        self._reset_time = time.time() + per
        self.count = 0
        self.logger = logger
        self.half_limit = limit // 2
        self.pool = pool
        self.warned = []

    async def invoke(self, ctx: commands.Context) -> bool:
        """
        Invokes the ratelimiter and runs checks against the relevant ratelimit.

        :param ctx: The context of the command being invoked.
        :type ctx: commands.Context
        """

        # Check when the ratelimit was last reset
        if self._reset_time < time.time():
            self._reset_time = time.time() + self.per

        # Insert the new call into the database
        async with self.pool.acquire() as conn:
            await conn.execute(
                'INSERT INTO calls VALUES ($1, $2, $3)',
                ctx.author.id,
                ctx.guild.id if ctx.guild is not None else 0,
                time.time().__trunc__(),
            )

            # Check the total number of calls in the last 30 seconds from the database
            calls = await conn.fetchval(
                'SELECT COUNT(*) FROM calls WHERE call_time > $1',
                self._reset_time,
            )
            if calls > self.limit:
                self.logger.warning(
                    f"Ratelimit exceeded at {calls} calls in the last 30 seconds."
                )
                return False

            # Check the number of calls from the user in the last 30 seconds
            calls = await conn.fetchval(
                'SELECT COUNT(*) FROM calls WHERE user_id = $1 AND call_time > $2',
                ctx.author.id,
                self._reset_time,
            )
            if calls > self.half_limit:
                self.logger.warning(
                    f"User ratelimit exceeded at {calls} calls from {ctx.author.id} in the last 30 seconds."
                )
                await ctx.send(f"You have used too many commands recently. Please wait {self.per} seconds before "
                               f"trying again.")
                return False

            # Checks have passed, return True
            return True
