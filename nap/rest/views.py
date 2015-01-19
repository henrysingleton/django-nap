from __future__ import unicode_literals

from django.core.exceptions import ValidationError
from django.views.generic import View, SingleObjectMixin, MultipleObjectMixin

from .. import http
from ..utils import JsonMixin, flatten_errors


class SerialisedResponseMixin(object):
    '''
    Passes context data through a
    '''
    content_type = 'application/json'
    response_class = http.JsonResponse

    def render_to_response(self, context, **response_kwargs):
        response_class = response_kwargs.pop('response_class', self.response_class)
        return response_class(context, **response_kwargs)

# TODO Add mixins for CRUD stages to process data through serialisers


class MapperMixin(JsonMixin):
    queryset = None
    mapper = None
    response_class = http.JsonResponse

    @property
    def model(self):
        return self.queryset.model

    def get_mapper(self):
        return self.mapper()

    def error_response(self, errors):
        return self.response_class(
            flatten_errors(errors),
            status=http.STATUS.BAD_REQUEST
        )


class ObjectMixin(MapperMixin, SingleObjectMixin):
    pass


class ObjectReadMixin(object):

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        mapper = self.get_mapper()

        return self.response_class(mapper << self.object)


class ObjectUpdateMixin(object):

    def put(self, request, *args, **kwargs):
        self.object = self.get_object()
        data = self.get_request_data({})

        mapper = self.get_mapper()

        try:
            mapper._apply(data)
        except ValidationError as e:
            return self.error_response(e.error_dict)

        self.object.save()

        return self.response_class(mapper << self.object)


class ObjectDeleteMixin(object):

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()

        return self.response_class(status=http.STATUS.NO_CONTENT)


class ListMixin(MapperMixin, MultipleObjectMixin):
    pass


class ListReadMixin(object):

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()

        mapper = self.get_mapper()

        return self.response_class([
            mapper << obj
            for obj in self.object_list
        ])


class ListCreateMixin(object):

    def post(self, request, *args, **kwargs):
        data = self.get_request_data({})
        mapper = self.get_mapper(self.model())

        try:
            self.object = mapper._apply(data)
        except ValidationError as e:
            return self.error_response(e.error_dict)

        self.object.save()

        return self.response_class(
            mapper._reduce(),
            status=http.STATUS.CREATED
        )
