# Extracted functions from the bot file

# self._session is defined as the following
def _create_session(self) -> aiohttp.ClientSession:
    """
    A helper function to create the aiohttp client session for the bot to use.

    :return: aiohttp.ClientSession
    """
    session = aiohttp.ClientSession(headers=self.config["headers"])
    return session

async def queue(
        self,
        unique_id: str,
        request_url: object,
        request_type: str,
        ctx: commands.Context,
        data: object = None,
) -> dict:
    """
    NS API request queue handler. Returns a dictionary object containing information on the request.

    :param data:
    :param request_type: str
    :param unique_id: str
    :param request_url: str
    :param ctx: commands.Context
    :return: dict
    """
    lim = await self.ns_ratelimiter.invoke(ctx)
    if lim is False:
        return {
            "unique_id": unique_id,
            "status": "ratelimited",
        }
    else:
        # We're good to go.
        if request_type.lower() == "get":
            try:
                r = await self.make_request(request_url, request_type)
            except aiohttp.ClientError as e:
                return {"unique_id": unique_id, "status": "error", "error": e}
        elif request_type.lower() == "post":
            try:
                r = await self.make_request(request_url, request_type, data=data)
            except aiohttp.ClientError as e:
                return {"unique_id": unique_id, "status": "error", "error": e}
        else:
            return {
                "unique_id": unique_id,
                "status": "error",
                "error": "Invalid request type.",
            }
        if r.status == 200:
            text = await r.text()
            return {
                "unique_id": unique_id,
                "status": "success",
                "response": text,
            }
        else:
            text = await r.text()
            return {
                "unique_id": unique_id,
                "status": r.status,
                "response": text,
            }
          
async def make_request(self, request_url, r_type="get", headers=True, data=None):
  """
  A simple function to manage the request-making of the bot and reduce boilerplate.
  While this is ideally an internal function, it can also be used in the event that a cog
  needs access to a web request.

  :param data:
  :param headers:
  :param request_url:
  :param r_type:
  :return:
  """

  if headers is True:
      # Headers are for NS only. It's assumed that a request is for NS, but
      # in the case that it isn't, do not pass the headers.
      if r_type.lower() == "get":
          try:
              return await self._session.get(request_url)
          except aiohttp.ClientError as e:
              self.logger.error(f"Error making request to {request_url}.")
      if r_type.lower() == "post":
          return await self._session.post(request_url, data=data)
  else:
      # There should be no headers attached to this request.
      if r_type.lower() == "get":
          return await self._session.get(request_url, headers=None)
      if r_type.lower() == "post":
          return await self._session.post(request_url, headers=None, data=data)
