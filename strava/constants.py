class EnumCollection(dict):

    def __getattr__(self, name):
        if self.get(name):
            return self[name]
        return super(self, EnumCollection).__getattr__(name)

    def __contains__(self, value):
        return value in self.values()


APPROVAL_PROMPT = EnumCollection(
    AUTO='auto',
    FORCE='force',
)

SCOPE = EnumCollection(
    READ='read',
    READ_ALL='read_all',
    PROFILE_READ_ALL='profile:read_all',
    PROFILE_WRITE='profile:write',
    ACTIVITY_READ='activity:read',
    ACTIVITY_READ_ALL='activity:read_all',
    ACTIVITY_WRITE='activity:write',
)
